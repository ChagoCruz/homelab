import re
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import date
import json


STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "with",
    "from",
    "in",
    "of",
    "for",
    "total",
    "calories",
    "calorie",
    "how",
    "many",
    "piece",
    "pieces",
    "pc",
}


TOKEN_ALIASES = {
    "4": "four",
    "four": "four",

    "lg": "large",
    "lrg": "large",
    "large": "large",

    "med": "medium",
    "md": "medium",
    "medium": "medium",

    "culver": "culvers",
    "culvers": "culvers",
    "culver's": "culvers",

    "tender": "tenders",
    "tenders": "tenders",

    "fry": "fry",
    "fries": "fry",
}


def normalize_text(value: str) -> str:
    value = value.lower()
    value = value.replace("'s", "s")
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def normalize_token(token: str) -> str:
    return TOKEN_ALIASES.get(token, token)


def tokenize_food(value: str) -> set[str]:
    normalized = normalize_text(value)

    tokens = set()

    for raw_token in normalized.split():
        if len(raw_token) < 2:
            continue

        token = normalize_token(raw_token)

        if token in STOPWORDS:
            continue

        tokens.add(token)

    return tokens


def build_requested_query(foods: list[str], original_message: str | None = None) -> str:
    """
    Prefer original_message because Ollama may expand user phrases in ways that
    do not match the user's historical food text.

    Example:
    Original: "culvers four pc and large fry"
    Parsed: ["Culver's 4 piece tenders", "large fry"]

    The original is closer to the DB row:
    "culvers four pc lg fry"
    """
    if original_message:
        return original_message

    return " ".join(food.strip() for food in foods if food.strip())


def score_food_match(requested_text: str, candidate_text: str) -> float:
    requested_tokens = tokenize_food(requested_text)
    candidate_tokens = tokenize_food(candidate_text)

    if not requested_tokens or not candidate_tokens:
        return 0.0

    overlap = requested_tokens.intersection(candidate_tokens)

    recall = len(overlap) / len(requested_tokens)

    extra_tokens = candidate_tokens - requested_tokens
    extra_penalty = len(extra_tokens) * 0.15

    score = recall - extra_penalty

    return max(score, 0.0)


def search_past_diet_entries(
    db: Session,
    foods: list[str],
    original_message: str | None = None,
) -> list[dict]:
    requested_text = build_requested_query(foods, original_message)
    requested_tokens = tokenize_food(requested_text)

    if not requested_tokens:
        return []

    conditions = []
    params = {}

    for idx, token in enumerate(requested_tokens):
        key = f"token_{idx}"
        conditions.append(f"food ILIKE :{key}")
        params[key] = f"%{token}%"

    sql = text(f"""
        SELECT
            id,
            food,
            calories,
            meal,
            log_date,
            confidence
        FROM diet
        WHERE {" OR ".join(conditions)}
        ORDER BY log_date DESC
        LIMIT 75
    """)

    rows = db.execute(sql, params).mappings().all()

    scored_matches = []

    for row in rows:
        row_dict = dict(row)

        score = score_food_match(requested_text, row_dict["food"])
        row_dict["match_score"] = score

        # Require strong overlap.
        # For "culvers four pc and large fry":
        # requested tokens -> culvers, four, large, fry
        # candidate tokens -> culvers, four, large, fry
        # score -> 1.0
        if score >= 0.75:
            scored_matches.append(row_dict)

    scored_matches.sort(
        key=lambda row: (
            row["match_score"],
            row["log_date"],
        ),
        reverse=True,
    )

    return scored_matches[:10]


def estimate_calories_from_past_entries(
    db: Session,
    foods: list[str],
    original_message: str | None = None,
) -> dict | None:
    matches = search_past_diet_entries(
        db=db,
        foods=foods,
        original_message=original_message,
    )

    if not matches:
        return None
    
    # Only average the best matching group.
    # This prevents bigger combo meals from polluting the estimate.
    top_score = matches[0]["match_score"]

    top_matches = [
        row for row in matches
        if row.get("match_score", 0) >= top_score - 0.001
    ]

    calorie_values = [
        row["calories"]
        for row in top_matches
        if row.get("calories") is not None
    ]

    if not calorie_values:
        return None

    average = round(sum(calorie_values) / len(calorie_values))

    return {
        "calories": average,
        "source": "past_entries",
        "confidence": "high" if len(top_matches) >= 3 else "medium",
        "matches_found": len(top_matches),
        "matches": top_matches,
    }

def json_safe(value):
    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, list):
        return [json_safe(item) for item in value]

    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}

    return value

def create_pending_diet_entry_action(
    db: Session,
    food: str,
    calories: int,
    meal: str | None,
    log_date: date,
    source: str,
    confidence: str,
    matches: list[dict] | None = None,
) -> dict:
    payload = json_safe({
        "food": food,
        "calories": calories,
        "meal": meal,
        "log_date": log_date.isoformat(),
        "source": source,
        "confidence": confidence,
        "matches": matches or [],
    })

    sql = text("""
        INSERT INTO assistant_pending_actions (
            action_type,
            payload,
            status
        )
        VALUES (
            'add_diet_entry',
            CAST(:payload AS JSONB),
            'pending'
        )
        RETURNING id, action_type, payload, status, created_at, expires_at
    """)

    row = db.execute(
        sql,
        {
            "payload": json.dumps(payload),
        },
    ).mappings().first()

    db.commit()
    return dict(row)


def get_latest_pending_diet_entry_action(db: Session) -> dict | None:
    sql = text("""
        SELECT id, action_type, payload, status, created_at, expires_at
        FROM assistant_pending_actions
        WHERE action_type = 'add_diet_entry'
          AND status = 'pending'
          AND expires_at > now()
        ORDER BY created_at DESC
        LIMIT 1
    """)

    row = db.execute(sql).mappings().first()
    return dict(row) if row else None


def complete_pending_action(db: Session, pending_action_id: int) -> None:
    sql = text("""
        UPDATE assistant_pending_actions
        SET status = 'completed',
            completed_at = now()
        WHERE id = :id
    """)

    db.execute(sql, {"id": pending_action_id})
    db.commit()


def cancel_pending_action(db: Session, pending_action_id: int) -> None:
    sql = text("""
        UPDATE assistant_pending_actions
        SET status = 'cancelled',
            completed_at = now()
        WHERE id = :id
    """)

    db.execute(sql, {"id": pending_action_id})
    db.commit()


def add_diet_entry_from_pending_payload(
    db: Session,
    payload: dict,
    meal_override: str | None = None,
) -> dict:
    meal = meal_override or payload.get("meal") or "unknown"

    sql = text("""
        INSERT INTO diet (
            log_date,
            meal,
            food,
            calories,
            confidence
        )
        VALUES (
            :log_date,
            :meal,
            :food,
            :calories,
            :confidence
        )
        RETURNING id, log_date, meal, food, calories, confidence
    """)

    row = db.execute(
        sql,
        {
            "log_date": payload["log_date"],
            "meal": meal,
            "food": payload["food"],
            "calories": payload["calories"],
            "confidence": payload.get("confidence", "medium"),
        },
    ).mappings().first()

    db.commit()
    return dict(row)