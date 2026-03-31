from __future__ import annotations

from typing import Any, Optional
import json
import os
import re

from anthropic import Anthropic
from fastapi import HTTPException

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")

_client = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise HTTPException(
                status_code=503,
                detail="AI insights unavailable: ANTHROPIC_API_KEY is not configured.",
            )
        _client = Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def _truncate_text(text: str, max_chars: int = 2500) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[Truncated for analysis]"


def _message(system_prompt: str, user_prompt: str, max_tokens: int = 900) -> str:
    try:
        response = _get_client().messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ],
        )

        parts: list[str] = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)

        text = "\n".join(parts).strip()
        if not text:
            raise HTTPException(status_code=502, detail="Claude returned an empty response.")
        return text
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Claude request failed: {e}")


def _extract_first_balanced_object(text: str) -> Optional[str]:
    """
    Finds the first balanced JSON object-like block in a string.
    """
    start = text.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escaped = False

        for idx in range(start, len(text)):
            char = text[idx]

            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == "\"":
                    in_string = False
                continue

            if char == "\"":
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : idx + 1]

        start = text.find("{", start + 1)

    return None


def _normalize_json_candidate(candidate: str) -> str:
    normalized = candidate.strip()
    normalized = normalized.replace("\ufeff", "")
    normalized = normalized.replace("“", "\"").replace("”", "\"")
    normalized = normalized.replace("‘", "'").replace("’", "'")

    if normalized.lower().startswith("json\n"):
        normalized = normalized.split("\n", 1)[1]

    # Common model mistake: trailing commas in JSON objects/arrays.
    normalized = re.sub(r",\s*([}\]])", r"\1", normalized)
    return normalized


def _iter_json_candidates(text: str):
    seen = set()

    def _yield(candidate: str):
        candidate = candidate.strip()
        if not candidate or candidate in seen:
            return
        seen.add(candidate)
        yield candidate

    stripped = text.strip()
    for candidate in _yield(stripped):
        yield candidate

    fences = re.findall(r"```(?:json)?\s*([\s\S]*?)```", stripped, flags=re.IGNORECASE)
    for fenced in fences:
        for candidate in _yield(fenced):
            yield candidate

    balanced = _extract_first_balanced_object(stripped)
    if balanced:
        for candidate in _yield(balanced):
            yield candidate

    for fenced in fences:
        balanced_fenced = _extract_first_balanced_object(fenced)
        if balanced_fenced:
            for candidate in _yield(balanced_fenced):
                yield candidate


def _parse_json_dict(candidate: str) -> Optional[dict[str, Any]]:
    attempts = [candidate, _normalize_json_candidate(candidate)]
    for attempt in attempts:
        try:
            data = json.loads(attempt)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


JSON_REPAIR_SYSTEM_PROMPT = """
You are a strict JSON repair utility.

You will receive malformed or noisy text that is intended to represent a JSON object.
Return ONLY one valid JSON object.

Rules:
- Keep the original keys and values whenever possible.
- Do not add markdown, prose, or code fences.
- If a value is unclear, preserve it as a string.
- If there is no recoverable object, return {}.
""".strip()


def _extract_json(text: str, allow_repair: bool = True) -> dict[str, Any]:
    """
    Attempts to parse a JSON object from the model output.
    """
    text = text.strip()

    for candidate in _iter_json_candidates(text):
        parsed = _parse_json_dict(candidate)
        if parsed is not None:
            return parsed

    if allow_repair:
        try:
            repaired = _message(
                system_prompt=JSON_REPAIR_SYSTEM_PROMPT,
                user_prompt=f"Repair this output into valid JSON:\n\n{text}",
                max_tokens=1200,
            )
            return _extract_json(repaired, allow_repair=False)
        except HTTPException:
            pass

    raise HTTPException(
        status_code=502,
        detail="Claude returned invalid JSON for structured output.",
    )


ENTRY_ANALYSIS_SYSTEM_PROMPT = """
You are a reflective personal therapist and life analyst.

Your role is not to judge or diagnose, but to help the user understand patterns
in their thoughts, emotions, and behaviors.

Analyze the following journal entry.

Focus on identifying:

Emotional signals
- emotional tone
- key emotions
- possible underlying feelings

Positive signals
- positive moments
- motivation
- creative excitement
- progress or growth

Stress signals
- possible stressors
- burnout signals
- self doubt
- perfectionism
- frustration

Behavioral patterns
- recurring motivations
- repeated concerns
- thinking patterns
- motivation cycles

Life direction signals
- career interests
- creative interests
- personal values
- long-term motivations

Also generate:
- a mood score from -5 to 5
- three thoughtful reflection questions that help the user explore their thoughts more deeply
- a short therapist-style insight (maximum 2 sentences)
- gentle encouragement or perspective (not prescriptive advice)

Return ONLY valid JSON with the following structure:

{
  "mood_score": 0,
  "emotional_tone": "",
  "key_emotions": [],
  "stressors": [],
  "positive_signals": [],
  "thinking_patterns": [],
  "life_direction_signals": [],
  "insight": "",
  "reflection_questions": [],
  "encouragement": ""
}

If information is not present in the journal entry, return an empty array or empty string rather than guessing.
""".strip()

JOURNAL_SUMMARY_SYSTEM_PROMPT = """
You are a reflective therapist helping someone understand the emotional and psychological story of their recent experiences.

You are summarizing multiple journal entry analyses across a time period.

Your goal is to gently describe what this period felt like, what themes emerged,
and what emotional shifts or patterns may have been present.

Return ONLY valid JSON in this shape:

{
  "summary": "",
  "themes": [],
  "emotional_trends": [],
  "stress_patterns": [],
  "positive_patterns": [],
  "direction_signals": [],
  "reflection_questions": []
}

Field guidance:
- summary: a warm, reflective narrative (3–6 sentences) describing the emotional arc of the period
- themes: recurring themes or concerns
- emotional_trends: shifts or repeated emotional tendencies over time
- stress_patterns: repeated sources of tension or pressure
- positive_patterns: moments of relief, growth, motivation, or clarity
- direction_signals: signals about values, interests, or life direction
- reflection_questions: 2–4 thoughtful questions to help the user reflect deeper

Tone:
- calm, grounded, and therapist-like
- not overly clinical or robotic
- not overly poetic or dramatic

Rules:
- Base conclusions only on the provided analyses
- Do not diagnose or label the user
- Do not overstate certainty
- If a pattern is weak, omit it
"""


LONG_TERM_PROFILE_SYSTEM_PROMPT = """
You are a reflective therapist and long-term life pattern analyst.

Your role is to help the user understand recurring emotional, behavioral,
and motivational patterns across time.

You are analyzing multiple journal entry analyses from the same person.

Focus on identifying patterns that feel stable or repeatedly present,
rather than one-time reactions.

Your goal is to help the user see themselves more clearly.

Focus on identifying:

Emotional trends
- dominant emotional tones
- repeated emotional states
- average mood pattern over time

Recurring stress patterns
- repeated stressors
- burnout signals
- sources of frustration or emotional drain

Recurring positive patterns
- moments of motivation
- sources of energy
- activities or thoughts associated with improved mood

Thinking and behavior patterns
- self doubt
- perfectionism
- motivation cycles
- avoidance patterns
- persistence
- creative excitement
- emotional recovery patterns

Life direction signals
- recurring career interests
- recurring creative interests
- long-term motivations
- personal values
- themes that appear meaningful over time

Growth and risk signals
- signs of progress
- signs of resilience
- signs of increased clarity
- possible recurring negative loops
- possible pressure points that may deserve reflection

Generate a grounded long-term pattern model based only on the information provided.

Return ONLY valid JSON with the following structure:

{
  "average_mood_score": 0,
  "dominant_emotions": [],
  "recurring_stressors": [],
  "recurring_positive_signals": [],
  "recurring_thinking_patterns": [],
  "recurring_life_direction_signals": [],
  "core_values": [],
  "motivation_drivers": [],
  "growth_signals": [],
  "risk_signals": [],
  "pattern_summary": ""
}

Rules:
- Base conclusions only on repeated or supported patterns across entries.
- Do not diagnose mental health conditions or assign fixed personality labels.
- Do not overstate certainty.
- If a pattern is weak or unclear, omit it or return an empty array.
- If information is not present in the journal analyses, return an empty array or empty string rather than guessing.
""".strip()

WEEKLY_BEHAVIORAL_INSIGHT_SYSTEM_PROMPT = """
You are a behavioral analytics engine focused on decision-making.

IMPORTANT:
- Not all signals are equally important.
- You MUST prioritize signals the user can control.
- You MUST NOT present uncontrollable signals (like weather) as primary drivers unless no better signals exist.

INPUT:
- weekly_behavior_metrics
- aggregated_journal_analysis
- unified_correlations (includes confidence, direction, control_level, and sample size)

CLASSIFY EACH SIGNAL:
- controllable: calories, workouts, alcohol, safety_meeting
- semi_controllable: stress patterns, routines
- uncontrollable: weather

PRIORITIZATION RULES:
- Always prioritize controllable signals first.
- Only include uncontrollable signals as secondary insights.
- Do NOT label uncontrollable signals as strongest relationship when controllable options exist.

INTERPRETATION RULES:
- Translate data into meaning first, then support with numbers.
- Plain English first; avoid technical phrasing unless needed.
- Distinguish actionable signals vs informational context.
- Do not output generic advice.

OUTPUT FORMAT (REQUIRED IN JSON FIELDS):
- this_week_in_one_line: exactly one sentence, plain English, no numbers, strongest controllable lever only
- key_insights: 3–4 concise bullets in plain English. Must include:
  - strongest controllable driver
  - overall system state (stress/trend)
  - optional external factor labeled as non-actionable
- what_to_focus_on: exactly 3 bullets:
  - Primary lever
  - Secondary lever
  - What to ignore for now
- system_state
- top_drivers (controllable first; uncontrollable only if necessary and clearly labeled)
- correlations
- patterns
- risk_flags
- recommendations (must map directly to controllable drivers; no weather-based recommendations)

Return ONLY valid JSON with this structure:
{
  "this_week_in_one_line": "",
  "key_insights": [],
  "what_to_focus_on": [],
  "system_state": "",
  "top_drivers": [
    { "driver": "", "evidence": "" }
  ],
  "correlations": [
    {
      "correlation": "",
      "strength": "weak",
      "confidence": "low",
      "control_level": "controllable",
      "interpretation": ""
    }
  ],
  "patterns": [],
  "risk_flags": [],
  "recommendations": [],
  "evidence_quality": ""
}

Allowed values:
- strength: weak | moderate | strong
- confidence: low | medium | high
- control_level: controllable | semi_controllable | uncontrollable

Limits:
- this_week_in_one_line: exactly 1 sentence
- top_drivers: max 3
- correlations: max 2
- recommendations: exactly 3 when possible
- key_insights: 3 to 4
- what_to_focus_on: exactly 3
""".strip()


def analyze_journal_entry_structured(entry: dict[str, Any]) -> dict[str, Any]:
    content = _truncate_text(entry.get("content", ""), max_chars=2500)

    user_prompt = (
        "Journal entry:\n"
        f"Entry date: {entry['entry_date']}\n"
        f"Content:\n{content}\n"
    )

    raw = _message(
        system_prompt=ENTRY_ANALYSIS_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=900,
    )
    return _extract_json(raw)

def build_journal_period_summary(
    analyses: list[dict[str, Any]],
    period_type: str,
    period_start: str,
    period_end: str,
) -> dict[str, Any]:
    payload = {
        "period_type": period_type,
        "period_start": period_start,
        "period_end": period_end,
        "analyses": analyses,
    }

    raw = _message(
        system_prompt=JOURNAL_SUMMARY_SYSTEM_PROMPT,
        user_prompt=f"Journal entry analyses:\n{json.dumps(payload, default=str)}",
        max_tokens=1100,
    )

    return _extract_json(raw)

def build_journal_pattern_profile(
    analyses: list[dict[str, Any]],
    period_type: str,
    period_start: str,
    period_end: str,
) -> dict[str, Any]:
    serialized = {
        "period_type": period_type,
        "period_start": period_start,
        "period_end": period_end,
        "analyses": analyses,
    }

    raw = _message(
        system_prompt=LONG_TERM_PROFILE_SYSTEM_PROMPT,
        user_prompt=f"Journal entry analyses:\n{json.dumps(serialized, default=str)}",
        max_tokens=1100,
    )
    return _extract_json(raw)


def build_weekly_behavioral_insight(
    payload: dict[str, Any],
) -> dict[str, Any]:
    raw = _message(
        system_prompt=WEEKLY_BEHAVIORAL_INSIGHT_SYSTEM_PROMPT,
        user_prompt=f"Weekly structured payload:\n{json.dumps(payload, default=str)}",
        max_tokens=1100,
    )
    return _extract_json(raw)


def _first_sentence(text_value: str, max_chars: int = 220) -> str:
    cleaned = " ".join(str(text_value or "").split())
    if not cleaned:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", cleaned, maxsplit=1)
    sentence = parts[0].strip() if parts else cleaned
    if len(sentence) <= max_chars:
        return sentence
    return sentence[: max_chars - 3].rstrip() + "..."


def _correlation_label(item: dict[str, Any]) -> str:
    return str(item.get("correlation") or item.get("comparison") or "").strip()


def _correlation_confidence_rank(item: dict[str, Any]) -> int:
    label = str(item.get("confidence") or "").strip().lower()
    return {"low": 0, "medium": 1, "high": 2}.get(label, 0)


def _correlation_strength_rank(item: dict[str, Any]) -> int:
    label = str(item.get("strength") or "").strip().lower()
    return {"weak": 0, "moderate": 1, "strong": 2}.get(label, 0)


def _correlation_sample_floor(item: dict[str, Any]) -> int:
    sample_size = item.get("sample_size") if isinstance(item.get("sample_size"), dict) else {}
    group_a = int(sample_size.get("group_a") or 0) if sample_size else 0
    group_b = int(sample_size.get("group_b") or 0) if sample_size else 0
    return min(group_a, group_b)


def _correlation_recommendation_relevance(item: dict[str, Any]) -> float:
    label = _correlation_label(item).lower()
    score = 0.0
    if any(token in label for token in ["calorie", "workout", "alcohol", "weed", "safety_meeting", "cannabis"]):
        score += 1.0
    if "next-day" in label or "after" in label:
        score += 0.2
    return score


def _correlation_outcome_priority(item: dict[str, Any]) -> int:
    label = _correlation_label(item).lower()
    if "mood" in label:
        return 2
    if any(token in label for token in ["blood pressure", "systolic", "diastolic", "bp"]):
        return 1
    return 0


def _sorted_correlations_by_priority(
    correlation_items: list[dict[str, Any]],
    *,
    control_level: str | None = None,
) -> list[dict[str, Any]]:
    candidates = [
        item
        for item in correlation_items
        if isinstance(item, dict)
        and (
            control_level is None
            or str(item.get("control_level") or "").lower() == control_level
        )
    ]
    if not candidates:
        return []

    best_confidence_rank = max(_correlation_confidence_rank(item) for item in candidates)
    confidence_tier = [
        item for item in candidates if _correlation_confidence_rank(item) == best_confidence_rank
    ]

    return sorted(
        confidence_tier,
        key=lambda item: (
            _correlation_recommendation_relevance(item),
            _correlation_outcome_priority(item),
            float(item.get("importance_score") or 0.0),
            float(item.get("confidence_score") or 0.0),
            _correlation_strength_rank(item),
            _correlation_sample_floor(item),
        ),
        reverse=True,
    )


def _contains_any(text_value: str, keywords: list[str]) -> bool:
    normalized = str(text_value or "").strip().lower()
    return any(keyword in normalized for keyword in keywords)


def _looks_like_state_or_risk(text_value: str) -> bool:
    normalized = str(text_value or "").strip().lower()
    if not normalized:
        return False
    if normalized.startswith(("primary lever:", "secondary lever:", "ignore for now:")):
        return False

    state_markers = [
        "entries were",
        "mood trended",
        "average mood",
        "appeared",
        "recurring stressor",
        "risk flag",
        "confidence",
        "delta",
        "n=",
        "high-stress",
        "was unfavorable",
    ]
    return "%" in normalized or any(marker in normalized for marker in state_markers)


def _action_from_context_text(context_text: str) -> str:
    normalized = str(context_text or "").strip().lower()

    # Prefer root-cause levers before symptom levers.
    if _contains_any(normalized, ["fear of rejection", "rejection"]):
        return "interrupt fear-of-rejection spirals by capping checking loops and forcing one concrete next step"

    if _contains_any(normalized, ["uncertainty", "uncertain", "waiting", "unknown"]):
        return "interrupt uncertainty spirals by turning waiting into one concrete action each day"

    if _contains_any(normalized, ["high-calorie", "calorie", "calories", "spike"]):
        return "stabilize daily calorie intake and reduce large day-to-day spikes"

    if _contains_any(normalized, ["workout", "exercise"]):
        return "protect at least three pre-scheduled workout slots this week"

    if _contains_any(normalized, ["alcohol", "drink", "drinking"]):
        return "set alcohol-free nights before priority mornings and track next-day mood/BP"

    if _contains_any(normalized, ["weed", "cannabis", "safety_meeting"]):
        return "plan no-weed evenings before priority mornings and compare next-day outcomes"

    if _contains_any(normalized, ["stress", "overwhelm", "pressure", "burnout"]):
        return "protect a 20-minute decompression block on high-pressure days"

    return "run one concrete behavior experiment for 7 days and review outcomes at week end"


def _action_from_correlation(item: dict[str, Any] | None) -> str:
    if not isinstance(item, dict):
        return ""
    return _action_from_context_text(
        " ".join(
            [
                _correlation_label(item),
                str(item.get("interpretation") or ""),
            ]
        )
    )


def _action_from_recommendations(
    recommendations: list[Any],
    *,
    exclude: set[str] | None = None,
) -> str:
    blocked = exclude or set()
    for recommendation in recommendations:
        sentence = _first_sentence(str(recommendation or ""))
        if not sentence:
            continue
        normalized = sentence.lower()
        if normalized in blocked:
            continue

        if _looks_like_state_or_risk(sentence):
            converted = _action_from_context_text(sentence)
            if converted and converted.lower() not in blocked:
                return converted
            continue

        return sentence
    return ""


def _as_action_clause(action_text: str) -> str:
    return str(action_text or "").strip().rstrip(".! ")


def _root_cause_lever(top_drivers: list[dict[str, Any]], risk_flags: list[Any]) -> str:
    context_parts: list[str] = []
    for driver in top_drivers[:3]:
        if not isinstance(driver, dict):
            continue
        context_parts.append(str(driver.get("driver") or ""))
        context_parts.append(str(driver.get("evidence") or ""))
    for risk in risk_flags[:3]:
        context_parts.append(str(risk or ""))
    context = " ".join(part for part in context_parts if part)
    return _action_from_context_text(context)


def _top_signal_implication(correlation: dict[str, Any] | None) -> str:
    if not isinstance(correlation, dict):
        return ""

    interpretation = str(correlation.get("interpretation") or "").lower()
    control_level = str(correlation.get("control_level") or "").lower()
    confidence = str(correlation.get("confidence") or "").lower()

    if control_level != "controllable":
        return "This matters because your top signal was not fully controllable, so treat it as context rather than a primary action target."

    if "less favorable" in interpretation or "unfavorable" in interpretation:
        base = "This matters because the strongest downside pattern this week was behavioral and controllable, not random."
    elif "more favorable" in interpretation:
        base = "This matters because your best pattern this week came from a controllable behavior you can repeat."
    else:
        base = "This matters because the clearest pattern this week came from a controllable behavior."

    if confidence == "low":
        return f"{base} Treat it as directional evidence while sample size grows."
    return base


def _plain_driver_takeaway(correlation: dict[str, Any] | None) -> str:
    if not isinstance(correlation, dict):
        return ""

    label = _correlation_label(correlation).lower()
    interpretation = str(correlation.get("interpretation") or "").lower()

    if "mood" in label:
        if "less favorable" in interpretation:
            return "When this pattern appears, mood tends to move in the wrong direction."
        if "more favorable" in interpretation:
            return "When this pattern appears, mood tends to stay more stable."
        return "This pattern appears to be directly linked to mood."

    if _contains_any(label, ["blood pressure", "systolic", "diastolic", "bp"]):
        if "less favorable" in interpretation:
            return "This pattern is linked to less stable blood-pressure outcomes."
        if "more favorable" in interpretation:
            return "This pattern is linked to more stable blood-pressure outcomes."
        return "This pattern appears to be linked to blood-pressure outcomes."

    return "This signal appears to be behavior-linked and actionable."


def _main_stress_driver_sentence(top_drivers: list[dict[str, Any]], risk_flags: list[Any]) -> str:
    for driver in top_drivers:
        if not isinstance(driver, dict):
            continue
        driver_label = str(driver.get("driver") or "").strip()
        normalized = driver_label.lower()
        if normalized.startswith("recurring stressor:"):
            stressor = driver_label.split(":", 1)[1].strip() if ":" in driver_label else driver_label
            if stressor:
                return f"The main stress loop this week was '{stressor}', which likely amplified emotional load."

    risk_blob = " ".join(str(item or "") for item in risk_flags)
    if _contains_any(risk_blob, ["high-stress", "stress", "overwhelm", "pressure"]):
        return "Stress stayed persistently elevated this week, so recovery capacity is still a central concern."

    return ""


def _build_this_week_in_one_line(
    *,
    top_drivers: list[dict[str, Any]],
    correlation_items: list[dict[str, Any]],
    risk_flags: list[Any],
    recommendations: list[Any],
) -> str:
    top_controllable = _pick_strongest_by_control(correlation_items, "controllable")
    label = _correlation_label(top_controllable).lower() if isinstance(top_controllable, dict) else ""

    if "calorie" in label and "mood" in label:
        return "Stabilizing your calorie intake is the clearest way to improve your mood right now."
    if "workout" in label and "mood" in label:
        return "Protecting consistent workouts is the clearest way to improve your mood right now."
    if "alcohol" in label and "mood" in label:
        return "Reducing alcohol before key days is the clearest way to protect your mood right now."
    if _contains_any(label, ["weed", "cannabis", "safety_meeting"]) and "mood" in label:
        return "Planning intentional no-weed evenings is the clearest way to support your mood right now."
    if _contains_any(label, ["systolic", "diastolic", "blood pressure", "bp"]):
        return "Your clearest controllable lever right now is tightening daily routines that support healthier blood pressure."

    action = _as_action_clause(_action_from_correlation(top_controllable))
    if not action:
        action = _as_action_clause(_root_cause_lever(top_drivers, risk_flags))
    if not action:
        action = _as_action_clause(_action_from_recommendations(recommendations))
    if not action:
        action = "protect one consistent controllable behavior each day"

    sentence = f"{action[:1].upper()}{action[1:]} is your clearest controllable lever this week."
    if re.search(r"\d", sentence):
        return "Focusing on one stable controllable routine is your clearest lever this week."
    return sentence


def _pick_strongest_by_control(
    correlation_items: list[dict[str, Any]],
    control_level: str,
) -> dict[str, Any] | None:
    candidates = _sorted_correlations_by_priority(correlation_items, control_level=control_level)
    if not candidates:
        return None
    return candidates[0]


def _build_key_insights(
    *,
    top_drivers: list[dict[str, Any]],
    correlation_items: list[dict[str, Any]],
    risk_flags: list[Any],
    recommendations: list[Any],
    system_state: str,
) -> list[str]:
    insights: list[str] = []
    seen: set[str] = set()

    def _add(item: str):
        sentence = _first_sentence(item)
        if not sentence:
            return
        key = sentence.lower()
        if key in seen:
            return
        seen.add(key)
        insights.append(sentence)

    controllable_top = _pick_strongest_by_control(correlation_items, "controllable")
    if controllable_top:
        corr_label = _correlation_label(controllable_top)
        plain_takeaway = _plain_driver_takeaway(controllable_top)
        if corr_label:
            _add(f"The clearest controllable signal this week was {corr_label}.")
        if plain_takeaway:
            _add(plain_takeaway)
        implication = _top_signal_implication(controllable_top)
        if implication:
            _add(implication)
    elif top_drivers:
        driver = str(top_drivers[0].get("driver") or "").strip()
        if driver:
            _add(f"Top driver this week: {driver}.")

    stress_driver_line = _main_stress_driver_sentence(top_drivers, risk_flags)
    if stress_driver_line:
        _add(stress_driver_line)

    _add(system_state)

    external_top = _pick_strongest_by_control(correlation_items, "uncontrollable")
    if external_top and str(external_top.get("confidence") or "").lower() in {"medium", "high"}:
        external_label = _correlation_label(external_top)
        if external_label:
            _add(f"External context: {external_label} may have contributed, but it is not the primary lever.")

    if risk_flags:
        risk_sentence = str(risk_flags[0]).strip()
        if risk_sentence and not _contains_any(risk_sentence, ["entries were", "delta", "n="]):
            _add(risk_sentence)

    if recommendations:
        _add(f"Most actionable next step right now: {str(recommendations[0])}")

    if len(insights) < 3:
        _add("Focus on the top two controllable behaviors first, then reassess next week.")

    return insights[:4]


def _build_what_to_focus_on(
    *,
    top_drivers: list[dict[str, Any]],
    correlation_items: list[dict[str, Any]],
    risk_flags: list[Any],
    recommendations: list[Any],
) -> list[str]:
    focus: list[str] = []
    seen: set[str] = set()

    def _add(item: str):
        sentence = _first_sentence(item)
        if not sentence:
            return
        key = sentence.lower()
        if key in seen:
            return
        seen.add(key)
        focus.append(sentence)

    controllable_sorted = _sorted_correlations_by_priority(
        correlation_items,
        control_level="controllable",
    )

    primary = controllable_sorted[0] if controllable_sorted else None
    secondary = controllable_sorted[1] if len(controllable_sorted) > 1 else None

    primary_action = _action_from_correlation(primary)
    if not primary_action:
        primary_action = _root_cause_lever(top_drivers, risk_flags)
    if not primary_action:
        primary_action = _action_from_recommendations(recommendations)
    primary_clause = _as_action_clause(primary_action)

    if primary:
        label = _correlation_label(primary) or "top controllable driver"
        _add(f"Primary lever: {primary_clause} (targets {label}).")
    elif primary_clause:
        _add(f"Primary lever: {primary_clause}.")

    secondary_action = ""
    if secondary:
        secondary_action = _action_from_correlation(secondary)
    if not secondary_action:
        secondary_action = _root_cause_lever(top_drivers, risk_flags)
    if not secondary_action:
        secondary_action = _action_from_recommendations(
            recommendations[1:],
            exclude={str(primary_action or "").lower()},
        )
    secondary_clause = _as_action_clause(secondary_action)
    if primary_clause and secondary_clause and secondary_clause.lower() == primary_clause.lower():
        alt_secondary = _as_action_clause(_root_cause_lever(top_drivers, risk_flags))
        if alt_secondary and alt_secondary.lower() != primary_clause.lower():
            secondary_clause = alt_secondary
        else:
            alt_secondary = _as_action_clause(
                _action_from_recommendations(
                    recommendations[1:],
                    exclude={primary_clause.lower()},
                )
            )
            if alt_secondary and alt_secondary.lower() != primary_clause.lower():
                secondary_clause = alt_secondary
            else:
                stress_context = " ".join(str(item or "") for item in risk_flags[:3])
                alt_secondary = _as_action_clause(_action_from_context_text(stress_context))
                if alt_secondary and alt_secondary.lower() != primary_clause.lower():
                    secondary_clause = alt_secondary

    if secondary_clause:
        _add(f"Secondary lever: {secondary_clause}.")

    external_top = _pick_strongest_by_control(correlation_items, "uncontrollable")
    if external_top:
        external_label = _correlation_label(external_top)
        if external_label:
            _add(f"Ignore for now: treat '{external_label}' as background context, not a behavior target.")
    else:
        _add("Ignore for now: one-off low-confidence signals that are not repeatable yet.")

    if not focus:
        _add("Primary lever: choose one controllable behavior and run it consistently for 7 days.")
        _add("Secondary lever: protect a short decompression block on high-pressure days.")
        _add("Ignore for now: weak signals until sample size improves.")

    return focus[:3]


def format_weekly_behavioral_insight(structured: dict[str, Any]) -> str:
    top_drivers = structured.get("top_drivers")
    if not isinstance(top_drivers, list):
        top_drivers = []

    correlations = structured.get("correlations")
    if not isinstance(correlations, list):
        correlations = []

    patterns = structured.get("patterns")
    if not isinstance(patterns, list):
        patterns = []

    risk_flags = structured.get("risk_flags")
    if not isinstance(risk_flags, list):
        risk_flags = []

    recommendations = structured.get("recommendations")
    if not isinstance(recommendations, list):
        recommendations = []

    system_state = str(structured.get("system_state") or "").strip()
    has_any_structured_sections = any(
        [
            any(isinstance(item, dict) and str(item.get("driver") or "").strip() for item in top_drivers),
            any(isinstance(item, dict) and str(item.get("correlation") or "").strip() for item in correlations),
            any(str(item).strip() for item in patterns),
            any(str(item).strip() for item in risk_flags),
            any(str(item).strip() for item in recommendations),
        ]
    )
    if not system_state:
        system_state = (
            "Unified analytics signal was sufficient to identify recurring drivers this week."
            if has_any_structured_sections
            else "Signal is limited this week."
        )

    driver_items = [item for item in top_drivers[:3] if isinstance(item, dict)]
    correlation_items = [item for item in correlations[:2] if isinstance(item, dict)]
    llm_one_line = str(structured.get("this_week_in_one_line") or "").strip()
    llm_key_insights = [str(item).strip() for item in (structured.get("key_insights") or []) if str(item).strip()]
    llm_what_to_focus_on = [
        str(item).strip()
        for item in (structured.get("what_to_focus_on") or [])
        if str(item).strip()
    ]

    fallback_one_line = _build_this_week_in_one_line(
        top_drivers=driver_items,
        correlation_items=correlation_items,
        risk_flags=risk_flags,
        recommendations=recommendations,
    )
    if llm_one_line and not re.search(r"\d", llm_one_line):
        this_week_in_one_line = _first_sentence(llm_one_line)
    else:
        this_week_in_one_line = fallback_one_line

    if llm_key_insights:
        key_insights = llm_key_insights[:4]
    else:
        key_insights = _build_key_insights(
            top_drivers=driver_items,
            correlation_items=correlation_items,
            risk_flags=risk_flags,
            recommendations=recommendations,
            system_state=system_state,
        )
    if llm_what_to_focus_on:
        what_to_focus_on = llm_what_to_focus_on[:3]
    else:
        what_to_focus_on = _build_what_to_focus_on(
            top_drivers=driver_items,
            correlation_items=correlation_items,
            risk_flags=risk_flags,
            recommendations=recommendations,
        )

    lines = [
        "[ THIS_WEEK_IN_ONE_LINE ]",
        this_week_in_one_line
        or "Focusing on one stable controllable routine is your clearest lever this week.",
        "",
        "[ KEY_INSIGHTS ]",
    ]

    if key_insights:
        for item in key_insights[:4]:
            lines.append(f"* {item}")
    else:
        lines.append("* Key insights are limited this week due to weak signal.")

    lines.extend(
        [
            "",
            "[ WHAT_TO_FOCUS_ON ]",
        ]
    )
    if what_to_focus_on:
        for item in what_to_focus_on[:3]:
            lines.append(f"* {item}")
    else:
        lines.append("* Focus on one controllable behavior and ignore weak/noisy signals for now.")

    lines.extend(
        [
            "",
            "[ SYSTEM_STATE ]",
            system_state,
            "",
            "[ TOP_DRIVERS ]",
        ]
    )

    if driver_items:
        for item in driver_items:
            driver = str(item.get("driver") or "Insufficient signal")
            evidence = str(item.get("evidence") or "Structured evidence is limited.")
            lines.append(f"* driver: {driver}")
            lines.append(f"  evidence: {evidence}")
    else:
        lines.append("* driver: Insufficient signal")
        lines.append("  evidence: Not enough structured evidence this week.")

    lines.append("")
    lines.append("[ CORRELATIONS ]")
    if correlation_items:
        for item in correlation_items:
            correlation = str(item.get("correlation") or "Insufficient signal")
            strength = str(item.get("strength") or "weak").lower()
            if strength not in {"weak", "moderate", "strong"}:
                strength = "weak"
            interpretation = str(item.get("interpretation") or "Limited signal.")
            interpretation = re.sub(r"\s*Confidence\s*(?:is|:)\s*[^.]+\.?", "", interpretation, flags=re.IGNORECASE).strip()
            confidence = str(item.get("confidence") or "").strip().lower()
            if confidence not in {"low", "medium", "high"}:
                confidence = ""
            sample_size = item.get("sample_size") if isinstance(item.get("sample_size"), dict) else {}
            group_a_n = int(sample_size.get("group_a") or 0) if sample_size else 0
            group_b_n = int(sample_size.get("group_b") or 0) if sample_size else 0
            sample_suffix = f" (n={group_a_n} vs n={group_b_n})" if (group_a_n or group_b_n) else ""
            lines.append(f"* correlation: {correlation}")
            lines.append(f"  interpretation: {interpretation}")
            lines.append(f"  strength: {strength}")
            if confidence:
                lines.append(f"  confidence: {confidence}{sample_suffix}")
            elif sample_suffix:
                lines.append(f"  sample_size: n={group_a_n} vs n={group_b_n}")
            control_level = str(item.get("control_level") or "").strip().lower()
            if control_level in {"controllable", "semi_controllable", "uncontrollable"}:
                lines.append(f"  control_level: {control_level}")
    else:
        lines.append("* correlation: Insufficient signal")
        lines.append("  strength: weak")
        lines.append("  confidence: low")
        lines.append("  interpretation: Not enough structured evidence this week.")

    lines.append("")
    lines.append("[ PATTERNS ]")
    if patterns:
        for item in patterns[:4]:
            lines.append(f"* {str(item)}")
    else:
        lines.append("* No recurring pattern met confidence threshold.")

    lines.append("")
    lines.append("[ RISK_FLAGS ]")
    if risk_flags:
        for item in risk_flags[:4]:
            lines.append(f"* {str(item)}")
    else:
        lines.append("* No clear risk flag from available structured data.")

    lines.append("")
    lines.append("[ RECOMMENDATIONS ]")
    if recommendations:
        for item in recommendations[:3]:
            lines.append(f"* {str(item)}")
    else:
        lines.append("* Keep data collection consistent for stronger signals next week.")

    return "\n".join(lines).strip()
