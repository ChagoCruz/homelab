from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
import json
import re
from typing import Any, Callable
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Journal, JournalEntryAnalysis, JournalPatternProfile
from app.schemas.journal_ai import JournalPatternProfileOut
from app.services.claude_service import (
    _build_key_insights,
    _build_what_to_focus_on,
    build_journal_pattern_profile,
    build_journal_period_summary,
    build_weekly_behavioral_insight,
    format_weekly_behavioral_insight,
)
from app.services.ollama_service import generate_weekly_report

router = APIRouter(prefix="/insights", tags=["insights"])
WEEKLY_BEHAVIORAL_PROMPT_VERSION = "v7-weekly-prioritized-decision-analytics"

class JournalWeeklyPeriodRequest(BaseModel):
    period_start: date | None = None
    period_end: date | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if (self.period_start is None) != (self.period_end is None):
            raise ValueError("period_start and period_end must be provided together")

        if self.period_start and self.period_end and self.period_start > self.period_end:
            raise ValueError("period_start must be on or before period_end")

        return self
    
def _resolve_weekly_window(payload: JournalWeeklyPeriodRequest | None) -> tuple[date, date]:
    if payload and payload.period_start and payload.period_end:
        return payload.period_start, payload.period_end

    period_end = date.today() - timedelta(days=1)
    period_start = period_end - timedelta(days=6)
    return period_start, period_end

def _load_weekly_analysis_rows(db: Session, period_start: date, period_end: date):
    return (
        db.query(JournalEntryAnalysis, Journal)
        .join(Journal, JournalEntryAnalysis.journal_entry_id == Journal.id)
        .filter(Journal.entry_date >= period_start, Journal.entry_date <= period_end)
        .order_by(Journal.entry_date.asc(), Journal.id.asc())
        .all()
    )

def _serialize_weekly_analyses(rows):
    analyses = []
    journal_ids = []
    mood_scores = []

    for analysis, journal in rows:
        journal_ids.append(journal.id)

        mood_value = float(analysis.mood_score) if analysis.mood_score is not None else None
        if mood_value is not None:
            mood_scores.append(mood_value)

        analyses.append(
            {
                "journal_entry_id": analysis.journal_entry_id,
                "entry_date": str(journal.entry_date),
                "mood_score": mood_value,
                "emotional_tone": analysis.emotional_tone,
                "key_emotions": analysis.key_emotions or [],
                "stressors": analysis.stressors or [],
                "positive_signals": analysis.positive_signals or [],
                "thinking_patterns": analysis.thinking_patterns or [],
                "life_direction_signals": analysis.life_direction_signals or [],
                "insight": analysis.insight,
                "reflection_questions": analysis.reflection_questions or [],
                "encouragement": analysis.encouragement,
            }
        )

    avg_mood = round(sum(mood_scores) / len(mood_scores), 2) if mood_scores else None
    return analyses, journal_ids, avg_mood


def _normalize_label(value: Any) -> str:
    if value is None:
        return ""
    normalized = " ".join(str(value).strip().lower().split())
    return normalized


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    return value


def _top_label_counts(groups: list[list[Any]], top_n: int = 5) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for group in groups:
        for item in group or []:
            label = _normalize_label(item)
            if label:
                counts[label] += 1
    return [{"label": label, "count": count} for label, count in counts.most_common(top_n)]


def aggregate_weekly_journal_analysis(analyses: list[dict[str, Any]]) -> dict[str, Any]:
    analyses_sorted = sorted(analyses, key=lambda item: str(item.get("entry_date") or ""))
    mood_points = [
        {
            "entry_date": str(item.get("entry_date")),
            "mood_score": _coerce_float(item.get("mood_score")),
        }
        for item in analyses_sorted
        if _coerce_float(item.get("mood_score")) is not None
    ]
    mood_scores = [point["mood_score"] for point in mood_points if point["mood_score"] is not None]

    mood_distribution = {
        "very_low": 0,
        "low": 0,
        "neutral": 0,
        "positive": 0,
        "very_positive": 0,
    }
    for score in mood_scores:
        if score <= -3:
            mood_distribution["very_low"] += 1
        elif score < -1:
            mood_distribution["low"] += 1
        elif score <= 1:
            mood_distribution["neutral"] += 1
        elif score < 3:
            mood_distribution["positive"] += 1
        else:
            mood_distribution["very_positive"] += 1

    mood_trend = {"direction": "insufficient_data", "delta": None}
    if len(mood_points) >= 2:
        delta = round((mood_points[-1]["mood_score"] or 0) - (mood_points[0]["mood_score"] or 0), 2)
        if delta >= 0.5:
            direction = "up"
        elif delta <= -0.5:
            direction = "down"
        else:
            direction = "flat"
        mood_trend = {
            "direction": direction,
            "delta": delta,
            "start_mood_score": mood_points[0]["mood_score"],
            "end_mood_score": mood_points[-1]["mood_score"],
        }

    high_stress_keywords = ("stress", "anx", "overwhelm", "burnout", "frustrat", "pressure")
    high_stress_entry_count = 0
    repeated_theme_counts: Counter[str] = Counter()
    repeated_theme_sources: dict[str, set[str]] = {}

    for item in analyses_sorted:
        mood_score = _coerce_float(item.get("mood_score"))
        stressors = item.get("stressors") or []
        emotional_tone = _normalize_label(item.get("emotional_tone"))

        is_high_stress = (
            (mood_score is not None and mood_score <= -2)
            or len(stressors) >= 2
            or any(keyword in emotional_tone for keyword in high_stress_keywords)
        )
        if is_high_stress:
            high_stress_entry_count += 1

        signal_groups = (
            ("key_emotions", item.get("key_emotions") or []),
            ("stressors", stressors),
            ("positive_signals", item.get("positive_signals") or []),
            ("thinking_patterns", item.get("thinking_patterns") or []),
            ("life_direction_signals", item.get("life_direction_signals") or []),
        )
        for source, signals in signal_groups:
            for signal in signals:
                label = _normalize_label(signal)
                if not label:
                    continue
                repeated_theme_counts[label] += 1
                repeated_theme_sources.setdefault(label, set()).add(source)

    repeated_themes = [
        {
            "theme": theme,
            "count": count,
            "sources": sorted(list(repeated_theme_sources.get(theme, set()))),
        }
        for theme, count in repeated_theme_counts.most_common(10)
        if count >= 2
    ]

    return {
        "entry_count": len(analyses_sorted),
        "average_mood_score": round(sum(mood_scores) / len(mood_scores), 2) if mood_scores else None,
        "mood_distribution": mood_distribution,
        "mood_trend": mood_trend,
        "dominant_emotions": _top_label_counts(
            [item.get("key_emotions") or [] for item in analyses_sorted],
            top_n=6,
        ),
        "top_stressors": _top_label_counts(
            [item.get("stressors") or [] for item in analyses_sorted],
            top_n=6,
        ),
        # "motivation drivers" are inferred from positive/life-direction signal recurrence.
        "top_motivation_drivers": _top_label_counts(
            [item.get("positive_signals") or [] for item in analyses_sorted]
            + [item.get("life_direction_signals") or [] for item in analyses_sorted],
            top_n=6,
        ),
        "high_stress_entry_count": high_stress_entry_count,
        "high_stress_entry_ratio": round(high_stress_entry_count / len(analyses_sorted), 2) if analyses_sorted else 0,
        "notable_repeated_themes": repeated_themes,
        "emotional_tone_counts": _top_label_counts(
            [[item.get("emotional_tone")] for item in analyses_sorted if item.get("emotional_tone")],
            top_n=6,
        ),
    }


def build_normalized_daily_rows(db: Session, period_start: date, period_end: date) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT
                day,
                avg_mood_score,
                avg_systolic,
                avg_diastolic,
                total_calories,
                had_alcohol,
                had_workout,
                total_workout_calories,
                safety_meeting,
                weather_summary,
                had_rain,
                had_clouds,
                had_sun,
                had_snow,
                temp_band
            FROM vw_daily_life_facts
            WHERE day BETWEEN :period_start AND :period_end
            ORDER BY day ASC
            """
        ),
        {"period_start": period_start, "period_end": period_end},
    ).mappings().all()

    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        row_day = row.get("day")
        if isinstance(row_day, str):
            try:
                row_day = date.fromisoformat(row_day)
            except ValueError:
                row_day = None
        if not isinstance(row_day, date):
            continue

        normalized_rows.append(
            {
                "day": row_day,
                "mood_score": _coerce_float(row.get("avg_mood_score")),
                "systolic": _coerce_float(row.get("avg_systolic")),
                "diastolic": _coerce_float(row.get("avg_diastolic")),
                "calories": _coerce_float(row.get("total_calories")),
                "alcohol": bool(row.get("had_alcohol")),
                "workout": bool(row.get("had_workout")),
                "workout_calories": _coerce_float(row.get("total_workout_calories")),
                "safety_meeting": bool(row.get("safety_meeting")),
                "weather_summary": str(row.get("weather_summary") or "").strip() or None,
                "rain": bool(row.get("had_rain")),
                "cloudy": bool(row.get("had_clouds")),
                "sunny": bool(row.get("had_sun")),
                "snow": bool(row.get("had_snow")),
                "temp_band": str(row.get("temp_band") or "").strip().lower() or None,
            }
        )

    return normalized_rows


def _load_daily_fact_rows(db: Session, period_start: date, period_end: date) -> list[dict[str, Any]]:
    # Backward-compatible helper: older callers expect JSONable rows.
    return [_to_jsonable(row) for row in build_normalized_daily_rows(db, period_start, period_end)]


def add_lag_flags(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows_sorted = sorted(
        rows,
        key=lambda item: item.get("day") if isinstance(item.get("day"), date) else date.min,
    )
    rows_by_day = {
        row["day"]: row
        for row in rows_sorted
        if isinstance(row, dict) and isinstance(row.get("day"), date)
    }

    enriched: list[dict[str, Any]] = []
    for row in rows_sorted:
        item = dict(row)
        item_day = item.get("day")
        prev_row = None
        if isinstance(item_day, date):
            prev_row = rows_by_day.get(item_day - timedelta(days=1))

        item["prev_day_workout"] = None if prev_row is None else bool(prev_row.get("workout"))
        item["prev_day_alcohol"] = None if prev_row is None else bool(prev_row.get("alcohol"))
        item["prev_day_safety_meeting"] = None if prev_row is None else bool(prev_row.get("safety_meeting"))
        enriched.append(item)

    return enriched


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    mid = len(sorted_values) // 2
    if len(sorted_values) % 2 == 0:
        return (sorted_values[mid - 1] + sorted_values[mid]) / 2
    return sorted_values[mid]


def _metric_higher_is_better(metric_family: str) -> bool:
    return metric_family == "mood"


def _effect_normalizer(metric_family: str) -> float:
    if metric_family == "mood":
        return 1.5
    if metric_family == "systolic_bp":
        return 8.0
    if metric_family == "diastolic_bp":
        return 5.0
    return 1.0


def _neutral_delta_threshold(metric_family: str) -> float:
    if metric_family == "mood":
        return 0.05
    return 0.5


def _normalized_effect_size(delta_abs: float, metric_family: str) -> float:
    normalizer = _effect_normalizer(metric_family)
    if normalizer <= 0:
        return 0.0
    return min(1.0, max(0.0, delta_abs / normalizer))


def _confidence_from_score(score: float, min_group_size: int) -> str:
    # Hard caps by sample size to avoid overstating tiny groups.
    if min_group_size < 3:
        return "low"
    if min_group_size < 5:
        if score >= 0.35:
            return "medium"
        return "low"
    if score >= 0.65:
        return "high"
    if score >= 0.35:
        return "medium"
    return "low"


def _confidence_rank(label: str) -> int:
    return {"low": 0, "medium": 1, "high": 2}.get(label, 0)


def _confidence_weight(label: str) -> float:
    return {"low": 0.2, "medium": 0.65, "high": 1.0}.get(label, 0.2)


def _control_level_from_context(category: str, key: str) -> str:
    normalized_category = str(category or "").lower()
    normalized_key = str(key or "").lower()

    if normalized_category.startswith("weather_"):
        return "uncontrollable"

    if any(token in normalized_key for token in ["sleep", "routine"]):
        return "semi_controllable"

    if normalized_category.startswith("behavior_") or normalized_category.startswith("substance_"):
        return "controllable"

    return "semi_controllable"


def _control_level_weight(control_level: str) -> float:
    if control_level == "controllable":
        return 0.5
    if control_level == "semi_controllable":
        return 0.25
    return 0.0


def _strength_from_effect(effect: float) -> str:
    if effect >= 0.6:
        return "strong"
    if effect >= 0.3:
        return "moderate"
    return "weak"


def _direction_from_delta(delta: float, metric_family: str) -> str:
    if abs(delta) <= _neutral_delta_threshold(metric_family):
        return "neutral"
    if _metric_higher_is_better(metric_family):
        return "positive" if delta > 0 else "negative"
    return "positive" if delta < 0 else "negative"


def compute_confidence_score(
    delta_abs: float,
    metric_family: str,
    group_a_size: int,
    group_b_size: int,
) -> float:
    normalized_delta = _normalized_effect_size(delta_abs, metric_family)
    min_group = min(group_a_size, group_b_size)
    max_group = max(group_a_size, group_b_size, 1)
    balance_factor = min_group / max_group

    # Strongly gate score by sample size.
    if min_group < 2:
        return 0.0
    if min_group < 3:
        size_factor = 0.2
    elif min_group < 5:
        size_factor = 0.5
    elif min_group < 8:
        size_factor = 0.75
    else:
        size_factor = 1.0

    score = normalized_delta * size_factor * (0.7 + (0.3 * balance_factor))
    return round(max(0.0, min(1.0, score)), 3)


def compare_groups(
    *,
    rows: list[dict[str, Any]],
    key: str,
    category: str,
    metric_family: str,
    metric_field: str,
    comparison: str,
    group_a_label: str,
    group_b_label: str,
    group_a_filter: Callable[[dict[str, Any]], bool],
    group_b_filter: Callable[[dict[str, Any]], bool],
    min_group_size: int = 2,
) -> dict[str, Any] | None:
    group_a_values: list[float] = []
    group_b_values: list[float] = []

    for row in rows:
        metric_value = _coerce_float(row.get(metric_field))
        if metric_value is None:
            continue
        if group_a_filter(row):
            group_a_values.append(metric_value)
        elif group_b_filter(row):
            group_b_values.append(metric_value)

    if len(group_a_values) < min_group_size or len(group_b_values) < min_group_size:
        return None

    group_a_avg = _mean(group_a_values)
    group_b_avg = _mean(group_b_values)
    if group_a_avg is None or group_b_avg is None:
        return None

    delta = round(group_a_avg - group_b_avg, 3)
    effect = _normalized_effect_size(abs(delta), metric_family)
    min_group = min(len(group_a_values), len(group_b_values))
    max_group = max(len(group_a_values), len(group_b_values), 1)
    total_group = len(group_a_values) + len(group_b_values)
    confidence_score = compute_confidence_score(
        delta_abs=abs(delta),
        metric_family=metric_family,
        group_a_size=len(group_a_values),
        group_b_size=len(group_b_values),
    )
    confidence = _confidence_from_score(confidence_score, min_group)
    confidence_rank = _confidence_rank(confidence)
    direction = _direction_from_delta(delta, metric_family)
    strength = _strength_from_effect(effect)
    control_level = _control_level_from_context(category=category, key=key)
    control_weight = _control_level_weight(control_level)

    # Ranking heavily prioritizes confidence tier, then confidence/effect blend, then sample balance.
    sample_balance = min_group / max_group
    confidence_weight = _confidence_weight(confidence)
    ranking_score = round(
        confidence_weight * ((0.65 * effect) + (0.35 * confidence_score)) * (0.75 + (0.25 * sample_balance)),
        3,
    )
    importance_score = round((confidence_score * abs(delta)) + control_weight, 3)

    if metric_family == "mood":
        metric_label = "mood"
    elif metric_family == "systolic_bp":
        metric_label = "systolic BP"
    else:
        metric_label = "diastolic BP"

    if direction == "neutral":
        interpretation = (
            f"{comparison} showed little measurable difference ({group_a_label} {group_a_avg:.2f} "
            f"vs {group_b_label} {group_b_avg:.2f})."
        )
    elif direction == "positive":
        interpretation = (
            f"{group_a_label} aligned with more favorable {metric_label} than {group_b_label} "
            f"({group_a_avg:.2f} vs {group_b_avg:.2f})."
        )
    else:
        interpretation = (
            f"{group_a_label} aligned with less favorable {metric_label} than {group_b_label} "
            f"({group_a_avg:.2f} vs {group_b_avg:.2f})."
        )

    return {
        "key": key,
        "category": category,
        "metric_family": metric_family,
        "comparison": comparison,
        # Legacy label retained for compatibility with older formatters/consumers.
        "correlation": comparison,
        "delta": delta,
        "direction": direction,
        "strength": strength,
        "control_level": control_level,
        "sample_size": {
            "group_a": len(group_a_values),
            "group_b": len(group_b_values),
        },
        "confidence_score": confidence_score,
        "confidence": confidence,
        "confidence_rank": confidence_rank,
        "evidence": {
            "group_a_label": group_a_label,
            "group_a_avg": group_a_avg,
            "group_b_label": group_b_label,
            "group_b_avg": group_b_avg,
        },
        "interpretation": interpretation,
        "ranking_score": ranking_score,
        "importance_score": importance_score,
        "min_group_size": min_group,
        "total_sample_size": total_group,
    }


def compute_unified_correlations(daily_rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = add_lag_flags(daily_rows)
    correlations: list[dict[str, Any]] = []

    calorie_values = [_coerce_float(row.get("calories")) for row in rows]
    calorie_values = [value for value in calorie_values if value is not None]
    median_calories = _median(calorie_values)

    def _append(candidate: dict[str, Any] | None):
        if candidate is not None:
            correlations.append(candidate)

    # Behavior -> mood
    _append(
        compare_groups(
            rows=rows,
            key="workout_same_day_mood",
            category="behavior_mood",
            metric_family="mood",
            metric_field="mood_score",
            comparison="Workout days vs non-workout days mood",
            group_a_label="workout days",
            group_b_label="non-workout days",
            group_a_filter=lambda row: row.get("workout") is True,
            group_b_filter=lambda row: row.get("workout") is False,
        )
    )
    _append(
        compare_groups(
            rows=rows,
            key="prev_workout_next_day_mood",
            category="behavior_mood",
            metric_family="mood",
            metric_field="mood_score",
            comparison="Next-day mood after workout vs no workout",
            group_a_label="next-day mood after workout",
            group_b_label="next-day mood after no workout",
            group_a_filter=lambda row: row.get("prev_day_workout") is True,
            group_b_filter=lambda row: row.get("prev_day_workout") is False,
        )
    )
    _append(
        compare_groups(
            rows=rows,
            key="prev_alcohol_next_day_mood",
            category="behavior_mood",
            metric_family="mood",
            metric_field="mood_score",
            comparison="Next-day mood after alcohol vs no alcohol",
            group_a_label="next-day mood after alcohol",
            group_b_label="next-day mood after no alcohol",
            group_a_filter=lambda row: row.get("prev_day_alcohol") is True,
            group_b_filter=lambda row: row.get("prev_day_alcohol") is False,
        )
    )
    if median_calories is not None:
        _append(
            compare_groups(
                rows=rows,
                key="high_calorie_same_day_mood",
                category="behavior_mood",
                metric_family="mood",
                metric_field="mood_score",
                comparison="High-calorie days vs lower-calorie days mood",
                group_a_label="high-calorie days",
                group_b_label="lower-calorie days",
                group_a_filter=lambda row: _coerce_float(row.get("calories")) is not None
                and (_coerce_float(row.get("calories")) or 0) >= median_calories,
                group_b_filter=lambda row: _coerce_float(row.get("calories")) is not None
                and (_coerce_float(row.get("calories")) or 0) < median_calories,
            )
        )

    # Behavior -> blood pressure
    for metric_field, metric_family, metric_label in [
        ("systolic", "systolic_bp", "systolic"),
        ("diastolic", "diastolic_bp", "diastolic"),
    ]:
        _append(
            compare_groups(
                rows=rows,
                key=f"workout_same_day_{metric_label}",
                category="behavior_bp",
                metric_family=metric_family,
                metric_field=metric_field,
                comparison=f"Workout days vs non-workout days {metric_label} BP",
                group_a_label="workout days",
                group_b_label="non-workout days",
                group_a_filter=lambda row: row.get("workout") is True,
                group_b_filter=lambda row: row.get("workout") is False,
            )
        )
        _append(
            compare_groups(
                rows=rows,
                key=f"prev_workout_next_day_{metric_label}",
                category="behavior_bp",
                metric_family=metric_family,
                metric_field=metric_field,
                comparison=f"Next-day {metric_label} BP after workout vs no workout",
                group_a_label="next-day BP after workout",
                group_b_label="next-day BP after no workout",
                group_a_filter=lambda row: row.get("prev_day_workout") is True,
                group_b_filter=lambda row: row.get("prev_day_workout") is False,
            )
        )
        _append(
            compare_groups(
                rows=rows,
                key=f"prev_alcohol_next_day_{metric_label}",
                category="behavior_bp",
                metric_family=metric_family,
                metric_field=metric_field,
                comparison=f"Next-day {metric_label} BP after alcohol vs no alcohol",
                group_a_label="next-day BP after alcohol",
                group_b_label="next-day BP after no alcohol",
                group_a_filter=lambda row: row.get("prev_day_alcohol") is True,
                group_b_filter=lambda row: row.get("prev_day_alcohol") is False,
            )
        )
        if median_calories is not None:
            _append(
                compare_groups(
                    rows=rows,
                    key=f"high_calorie_same_day_{metric_label}",
                    category="behavior_bp",
                    metric_family=metric_family,
                    metric_field=metric_field,
                    comparison=f"High-calorie days vs lower-calorie days {metric_label} BP",
                    group_a_label="high-calorie days",
                    group_b_label="lower-calorie days",
                    group_a_filter=lambda row: _coerce_float(row.get("calories")) is not None
                    and (_coerce_float(row.get("calories")) or 0) >= median_calories,
                    group_b_filter=lambda row: _coerce_float(row.get("calories")) is not None
                    and (_coerce_float(row.get("calories")) or 0) < median_calories,
                )
            )

    # Weather -> mood
    _append(
        compare_groups(
            rows=rows,
            key="rainy_same_day_mood",
            category="weather_mood",
            metric_family="mood",
            metric_field="mood_score",
            comparison="Rainy days vs non-rainy days mood",
            group_a_label="rainy days",
            group_b_label="non-rainy days",
            group_a_filter=lambda row: row.get("rain") is True,
            group_b_filter=lambda row: row.get("rain") is False,
        )
    )
    _append(
        compare_groups(
            rows=rows,
            key="cloudy_same_day_mood",
            category="weather_mood",
            metric_family="mood",
            metric_field="mood_score",
            comparison="Cloudy days vs non-cloudy days mood",
            group_a_label="cloudy days",
            group_b_label="non-cloudy days",
            group_a_filter=lambda row: row.get("cloudy") is True,
            group_b_filter=lambda row: row.get("cloudy") is False,
        )
    )
    _append(
        compare_groups(
            rows=rows,
            key="sunny_same_day_mood",
            category="weather_mood",
            metric_family="mood",
            metric_field="mood_score",
            comparison="Sunny days vs non-sunny days mood",
            group_a_label="sunny days",
            group_b_label="non-sunny days",
            group_a_filter=lambda row: row.get("sunny") is True,
            group_b_filter=lambda row: row.get("sunny") is False,
        )
    )
    _append(
        compare_groups(
            rows=rows,
            key="cold_vs_mild_mood",
            category="weather_mood",
            metric_family="mood",
            metric_field="mood_score",
            comparison="Cold/freezing days vs mild-or-warmer days mood",
            group_a_label="cold/freezing days",
            group_b_label="mild-or-warmer days",
            group_a_filter=lambda row: str(row.get("temp_band") or "") in {"cold", "freezing"},
            group_b_filter=lambda row: str(row.get("temp_band") or "") in {"mild", "warm", "hot"},
        )
    )

    # Weather -> blood pressure
    for metric_field, metric_family, metric_label in [
        ("systolic", "systolic_bp", "systolic"),
        ("diastolic", "diastolic_bp", "diastolic"),
    ]:
        _append(
            compare_groups(
                rows=rows,
                key=f"rainy_same_day_{metric_label}",
                category="weather_bp",
                metric_family=metric_family,
                metric_field=metric_field,
                comparison=f"Rainy days vs non-rainy days {metric_label} BP",
                group_a_label="rainy days",
                group_b_label="non-rainy days",
                group_a_filter=lambda row: row.get("rain") is True,
                group_b_filter=lambda row: row.get("rain") is False,
            )
        )
        _append(
            compare_groups(
                rows=rows,
                key=f"cloudy_same_day_{metric_label}",
                category="weather_bp",
                metric_family=metric_family,
                metric_field=metric_field,
                comparison=f"Cloudy days vs non-cloudy days {metric_label} BP",
                group_a_label="cloudy days",
                group_b_label="non-cloudy days",
                group_a_filter=lambda row: row.get("cloudy") is True,
                group_b_filter=lambda row: row.get("cloudy") is False,
            )
        )
        _append(
            compare_groups(
                rows=rows,
                key=f"sunny_same_day_{metric_label}",
                category="weather_bp",
                metric_family=metric_family,
                metric_field=metric_field,
                comparison=f"Sunny days vs non-sunny days {metric_label} BP",
                group_a_label="sunny days",
                group_b_label="non-sunny days",
                group_a_filter=lambda row: row.get("sunny") is True,
                group_b_filter=lambda row: row.get("sunny") is False,
            )
        )
        _append(
            compare_groups(
                rows=rows,
                key=f"cold_vs_mild_{metric_label}",
                category="weather_bp",
                metric_family=metric_family,
                metric_field=metric_field,
                comparison=f"Cold/freezing days vs mild-or-warmer days {metric_label} BP",
                group_a_label="cold/freezing days",
                group_b_label="mild-or-warmer days",
                group_a_filter=lambda row: str(row.get("temp_band") or "") in {"cold", "freezing"},
                group_b_filter=lambda row: str(row.get("temp_band") or "") in {"mild", "warm", "hot"},
            )
        )

    # Substance (safety_meeting) -> mood
    _append(
        compare_groups(
            rows=rows,
            key="no_weed_vs_weed_same_day_mood",
            category="substance_mood",
            metric_family="mood",
            metric_field="mood_score",
            comparison="No-weed days vs weed days mood",
            group_a_label="no-weed days",
            group_b_label="weed days",
            group_a_filter=lambda row: row.get("safety_meeting") is False,
            group_b_filter=lambda row: row.get("safety_meeting") is True,
        )
    )
    _append(
        compare_groups(
            rows=rows,
            key="no_weed_vs_weed_next_day_mood",
            category="substance_mood",
            metric_family="mood",
            metric_field="mood_score",
            comparison="Next-day mood after no-weed vs weed",
            group_a_label="next-day mood after no-weed",
            group_b_label="next-day mood after weed",
            group_a_filter=lambda row: row.get("prev_day_safety_meeting") is False,
            group_b_filter=lambda row: row.get("prev_day_safety_meeting") is True,
        )
    )

    # Substance (safety_meeting) -> blood pressure
    for metric_field, metric_family, metric_label in [
        ("systolic", "systolic_bp", "systolic"),
        ("diastolic", "diastolic_bp", "diastolic"),
    ]:
        _append(
            compare_groups(
                rows=rows,
                key=f"no_weed_vs_weed_same_day_{metric_label}",
                category="substance_bp",
                metric_family=metric_family,
                metric_field=metric_field,
                comparison=f"No-weed days vs weed days {metric_label} BP",
                group_a_label="no-weed days",
                group_b_label="weed days",
                group_a_filter=lambda row: row.get("safety_meeting") is False,
                group_b_filter=lambda row: row.get("safety_meeting") is True,
            )
        )
        _append(
            compare_groups(
                rows=rows,
                key=f"no_weed_vs_weed_next_day_{metric_label}",
                category="substance_bp",
                metric_family=metric_family,
                metric_field=metric_field,
                comparison=f"Next-day {metric_label} BP after no-weed vs weed",
                group_a_label="next-day BP after no-weed",
                group_b_label="next-day BP after weed",
                group_a_filter=lambda row: row.get("prev_day_safety_meeting") is False,
                group_b_filter=lambda row: row.get("prev_day_safety_meeting") is True,
            )
        )

    sorted_candidates = sorted(
        correlations,
        key=lambda item: (
            int(item.get("confidence_rank") or 0),
            _coerce_float(item.get("importance_score")) or 0.0,
            _coerce_float(item.get("ranking_score")) or 0.0,
            int(item.get("min_group_size") or 0),
            int(item.get("total_sample_size") or 0),
            _coerce_float(item.get("confidence_score")) or 0.0,
            abs(_coerce_float(item.get("delta")) or 0.0),
        ),
        reverse=True,
    )

    strongest = sorted_candidates[:6]
    behavior_correlations = [
        item
        for item in sorted_candidates
        if str(item.get("category") or "").startswith("behavior_")
    ]
    weather_correlations = [
        item
        for item in sorted_candidates
        if str(item.get("category") or "").startswith("weather_")
    ]
    substance_correlations = [
        item
        for item in sorted_candidates
        if str(item.get("category") or "").startswith("substance_")
    ]
    health_correlations = [
        item
        for item in sorted_candidates
        if str(item.get("category") or "").endswith("_bp")
    ]

    high_conf = sum(1 for item in sorted_candidates if str(item.get("confidence") or "") == "high")
    med_or_high_conf = sum(
        1
        for item in sorted_candidates
        if str(item.get("confidence") or "") in {"medium", "high"}
    )
    if not sorted_candidates:
        evidence_quality = "limited"
    elif high_conf >= 3 or med_or_high_conf >= 5:
        evidence_quality = "high"
    elif med_or_high_conf >= 2:
        evidence_quality = "usable"
    else:
        evidence_quality = "limited"

    return {
        "candidate_count": len(sorted_candidates),
        "all_correlations": sorted_candidates,
        "strongest_correlations": strongest,
        "behavior_correlations": behavior_correlations,
        "weather_correlations": weather_correlations,
        "health_correlations": health_correlations,
        "substance_correlations": substance_correlations,
        "evidence_quality": evidence_quality,
        "calorie_split_median": round(median_calories, 2) if median_calories is not None else None,
    }


def compute_behavior_correlations(daily_rows: list[dict[str, Any]]) -> dict[str, Any]:
    # Backward-compatible behavior-only projection from the unified engine.
    normalized_rows = daily_rows
    if normalized_rows and isinstance(normalized_rows[0], dict) and "mood_score" not in normalized_rows[0]:
        projected_rows: list[dict[str, Any]] = []
        for row in normalized_rows:
            row_day = row.get("day")
            if isinstance(row_day, str):
                try:
                    row_day = date.fromisoformat(row_day)
                except ValueError:
                    row_day = None
            if not isinstance(row_day, date):
                continue
            projected_rows.append(
                {
                    "day": row_day,
                    "mood_score": _coerce_float(row.get("avg_mood_score")),
                    "systolic": _coerce_float(row.get("avg_systolic")),
                    "diastolic": _coerce_float(row.get("avg_diastolic")),
                    "calories": _coerce_float(row.get("total_calories")),
                    "alcohol": bool(row.get("had_alcohol")),
                    "workout": bool(row.get("had_workout")),
                    "workout_calories": _coerce_float(row.get("total_workout_calories")),
                    "safety_meeting": bool(row.get("safety_meeting")),
                    "weather_summary": str(row.get("weather_summary") or "").strip() or None,
                    "rain": bool(row.get("had_rain")),
                    "cloudy": bool(row.get("had_clouds")),
                    "sunny": bool(row.get("had_sun")),
                    "snow": bool(row.get("had_snow")),
                    "temp_band": str(row.get("temp_band") or "").strip().lower() or None,
                }
            )
        normalized_rows = projected_rows

    unified = compute_unified_correlations(normalized_rows)
    behavior_only = unified.get("behavior_correlations") or []
    strongest = behavior_only[:2]

    return {
        "candidate_count": len(behavior_only),
        "strongest_correlations": strongest,
        "all_correlations": behavior_only,
        "evidence_quality": unified.get("evidence_quality") or "limited",
    }


def _load_weekly_behavior_metrics(db: Session, period_start: date, period_end: date) -> dict[str, Any]:
    exact_week = db.execute(
        text(
            """
            SELECT *
            FROM vw_weekly_life_summary
            WHERE week_start = :period_start
              AND week_end = :period_end
            LIMIT 1
            """
        ),
        {"period_start": period_start, "period_end": period_end},
    ).mappings().first()

    if exact_week:
        return {
            "source": "vw_weekly_life_summary",
            "window_alignment": "exact_week_view_match",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "metrics": _to_jsonable(dict(exact_week)),
        }

    # Fallback keeps weekly analytics available for rolling/custom 7-day windows.
    rollup = db.execute(
        text(
            """
            SELECT
                COUNT(*) AS days_with_data,
                COALESCE(SUM(journal_count), 0) AS journal_count,
                COALESCE(SUM(CASE WHEN had_journal THEN 1 ELSE 0 END), 0) AS days_with_journal,
                COALESCE(SUM(CASE WHEN had_journal_analysis THEN 1 ELSE 0 END), 0) AS days_with_journal_analysis,
                ROUND(AVG(avg_mood_score)::numeric, 2) AS avg_mood_score,
                ROUND(MIN(min_mood_score)::numeric, 2) AS min_mood_score,
                ROUND(MAX(max_mood_score)::numeric, 2) AS max_mood_score,
                COALESCE(SUM(food_entry_count), 0) AS food_entry_count,
                COALESCE(SUM(total_calories), 0) AS total_calories,
                ROUND(AVG(total_calories)::numeric, 2) AS avg_daily_calories,
                COALESCE(SUM(drink_entry_count), 0) AS drink_entry_count,
                COALESCE(SUM(alcohol_entry_count), 0) AS alcohol_entry_count,
                COALESCE(SUM(CASE WHEN had_alcohol THEN 1 ELSE 0 END), 0) AS alcohol_days,
                ROUND(AVG(avg_weight)::numeric, 2) AS avg_weight,
                ROUND(MIN(avg_weight)::numeric, 2) AS min_weight,
                ROUND(MAX(avg_weight)::numeric, 2) AS max_weight,
                ROUND(AVG(avg_systolic)::numeric, 2) AS avg_systolic,
                ROUND(AVG(avg_diastolic)::numeric, 2) AS avg_diastolic,
                COALESCE(SUM(workout_entry_count), 0) AS workout_entry_count,
                COALESCE(SUM(total_workout_calories), 0) AS total_workout_calories,
                ROUND(AVG(total_workout_calories)::numeric, 2) AS avg_daily_workout_calories,
                COALESCE(SUM(CASE WHEN had_workout THEN 1 ELSE 0 END), 0) AS workout_days,
                ROUND((COALESCE(SUM(total_calories), 0) - COALESCE(SUM(total_workout_calories), 0))::numeric, 2) AS net_calories,
                ROUND(AVG(temp_max_f)::numeric, 2) AS avg_temp_max_f,
                ROUND(AVG(temp_min_f)::numeric, 2) AS avg_temp_min_f,
                ROUND(MAX(temp_max_f)::numeric, 2) AS hottest_temp_f,
                ROUND(MIN(temp_min_f)::numeric, 2) AS coldest_temp_f,
                COALESCE(SUM(CASE WHEN had_rain THEN 1 ELSE 0 END), 0) AS rain_days,
                COALESCE(SUM(CASE WHEN had_snow THEN 1 ELSE 0 END), 0) AS snow_days,
                COALESCE(SUM(CASE WHEN had_clouds THEN 1 ELSE 0 END), 0) AS cloudy_days,
                COALESCE(SUM(CASE WHEN had_sun THEN 1 ELSE 0 END), 0) AS sunny_days,
                COALESCE(SUM(CASE WHEN safety_meeting THEN 1 ELSE 0 END), 0) AS safety_meeting_days
            FROM vw_daily_life_facts
            WHERE day BETWEEN :period_start AND :period_end
            """
        ),
        {"period_start": period_start, "period_end": period_end},
    ).mappings().first()

    overlapping_weeks = db.execute(
        text(
            """
            SELECT week_start, week_end, avg_mood_score, avg_daily_calories, workout_days, alcohol_days
            FROM vw_weekly_life_summary
            WHERE week_start <= :period_end
              AND week_end >= :period_start
            ORDER BY week_start ASC
            """
        ),
        {"period_start": period_start, "period_end": period_end},
    ).mappings().all()

    return {
        "source": "vw_daily_life_facts_rollup",
        "window_alignment": "rolling_or_custom_window_fallback",
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "expected_days": (period_end - period_start).days + 1,
        "metrics": _to_jsonable(dict(rollup or {})),
        "overlapping_week_context": _to_jsonable([dict(row) for row in overlapping_weeks]),
    }


def build_weekly_insight_payload(
    weekly_behavior_metrics: dict[str, Any],
    aggregated_journal_analysis: dict[str, Any],
    unified_correlations: dict[str, Any],
) -> dict[str, Any]:
    behavior_correlations = {
        "candidate_count": len(unified_correlations.get("behavior_correlations") or []),
        "strongest_correlations": (unified_correlations.get("behavior_correlations") or [])[:2],
        "all_correlations": unified_correlations.get("behavior_correlations") or [],
        "evidence_quality": unified_correlations.get("evidence_quality") or "limited",
    }
    return {
        "weekly_behavior_metrics": weekly_behavior_metrics,
        "aggregated_journal_analysis": aggregated_journal_analysis,
        "unified_correlations": unified_correlations,
        # Backward-compatible alias for older prompt/consumers.
        "behavior_correlations": behavior_correlations,
    }


def _is_current_weekly_behavior_format(structured_output: Any) -> bool:
    payload = structured_output
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return False
    if not isinstance(payload, dict):
        return False
    return isinstance(payload.get("top_drivers"), list) and isinstance(payload.get("correlations"), list)


def _has_populated_weekly_sections(structured_output: Any) -> bool:
    payload = structured_output
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return False
    if not isinstance(payload, dict):
        return False

    top_drivers = payload.get("top_drivers")
    correlations = payload.get("correlations")
    patterns = payload.get("patterns")
    risk_flags = payload.get("risk_flags")
    recommendations = payload.get("recommendations")

    return any(
        [
            isinstance(top_drivers, list) and len(top_drivers) > 0,
            isinstance(correlations, list) and len(correlations) > 0,
            isinstance(patterns, list) and len(patterns) > 0,
            isinstance(risk_flags, list) and len(risk_flags) > 0,
            isinstance(recommendations, list) and len(recommendations) > 0,
        ]
    )


def _sanitize_top_drivers(items: Any) -> list[dict[str, str]]:
    if not isinstance(items, list):
        return []
    normalized: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        driver = str(item.get("driver") or "").strip()
        if not driver:
            continue
        evidence = str(item.get("evidence") or "").strip()
        normalized.append(
            {
                "driver": driver,
                "evidence": evidence or "Structured evidence available.",
            }
        )
    return normalized


def _sanitize_correlations(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        correlation = str(item.get("correlation") or "").strip()
        if not correlation:
            continue
        strength = str(item.get("strength") or "weak").strip().lower()
        if strength not in {"weak", "moderate", "strong"}:
            strength = "weak"
        interpretation = _clean_interpretation_text(str(item.get("interpretation") or "").strip())
        if not interpretation:
            interpretation = "Structured signal is present."
        confidence = str(item.get("confidence") or "").strip().lower()
        confidence_score = _coerce_float(item.get("confidence_score"))
        control_level = str(item.get("control_level") or "").strip().lower()
        importance_score = _coerce_float(item.get("importance_score"))
        sample_size = item.get("sample_size") if isinstance(item.get("sample_size"), dict) else {}
        normalized.append(
            {
                "correlation": correlation,
                "strength": strength,
                "interpretation": interpretation,
                **({"confidence": confidence} if confidence in {"low", "medium", "high"} else {}),
                **({"confidence_score": confidence_score} if confidence_score is not None else {}),
                **(
                    {"control_level": control_level}
                    if control_level in {"controllable", "semi_controllable", "uncontrollable"}
                    else {}
                ),
                **({"importance_score": importance_score} if importance_score is not None else {}),
                **(
                    {
                        "sample_size": {
                            "group_a": int(sample_size.get("group_a") or 0),
                            "group_b": int(sample_size.get("group_b") or 0),
                        }
                    }
                    if sample_size
                    else {}
                ),
            }
        )
    return normalized


def _sanitize_string_list(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    return [str(item).strip() for item in items if str(item).strip()]


def _merge_driver_sections(primary: list[dict[str, str]], fallback: list[dict[str, str]], limit: int = 3) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in [*primary, *fallback]:
        key = _normalize_label(item.get("driver"))
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(item)
        if len(merged) >= limit:
            break
    return merged


def _merge_correlation_sections(primary: list[dict[str, Any]], fallback: list[dict[str, Any]], limit: int = 2) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in [*primary, *fallback]:
        key = _normalize_label(item.get("correlation"))
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(item)
        if len(merged) >= limit:
            break
    return merged


def _merge_string_sections(primary: list[str], fallback: list[str], limit: int) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for item in [*primary, *fallback]:
        key = _normalize_label(item)
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(item)
        if len(merged) >= limit:
            break
    return merged


def _prioritized_correlation_candidates(
    unified_correlations: dict[str, Any],
    limit: int = 2,
) -> list[dict[str, Any]]:
    all_correlations = [
        item
        for item in (unified_correlations.get("all_correlations") or [])
        if isinstance(item, dict)
    ]
    if not all_correlations:
        return []

    reliable = [
        item
        for item in all_correlations
        if str(item.get("confidence") or "").lower() in {"medium", "high"}
    ]
    controllable_reliable = [
        item
        for item in reliable
        if str(item.get("control_level") or "").lower() == "controllable"
    ]
    semi_reliable = [
        item
        for item in reliable
        if str(item.get("control_level") or "").lower() == "semi_controllable"
    ]
    uncontrollable_reliable = [
        item
        for item in reliable
        if str(item.get("control_level") or "").lower() == "uncontrollable"
    ]
    controllable_any = [
        item
        for item in all_correlations
        if str(item.get("control_level") or "").lower() == "controllable"
    ]

    selected: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    def _add_batch(items: list[dict[str, Any]]):
        for item in items:
            key = str(item.get("key") or "")
            if key and key in seen_keys:
                continue
            if key:
                seen_keys.add(key)
            selected.append(item)
            if len(selected) >= limit:
                break

    _add_batch(controllable_reliable)
    if len(selected) < limit:
        _add_batch(semi_reliable)
    # External factors should stay secondary and only appear when controllable/semi signals are sparse.
    if len(selected) < limit and not selected:
        _add_batch(uncontrollable_reliable)
    if len(selected) < limit:
        _add_batch(controllable_any)
    if len(selected) < limit:
        _add_batch(all_correlations)

    return selected[:limit]


def _primary_correlation_for_system_state(unified_correlations: dict[str, Any]) -> dict[str, Any] | None:
    prioritized = _prioritized_correlation_candidates(unified_correlations, limit=1)
    if prioritized:
        return prioritized[0]

    all_correlations = [
        item
        for item in (unified_correlations.get("all_correlations") or [])
        if isinstance(item, dict)
    ]
    if not all_correlations:
        return None
    return all_correlations[0]


def _correlation_lookup(unified_correlations: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for item in (unified_correlations.get("all_correlations") or []):
        if not isinstance(item, dict):
            continue
        label = str(item.get("comparison") or item.get("correlation") or "").strip()
        key = _normalize_label(label)
        if key and key not in lookup:
            lookup[key] = item
    return lookup


def _enrich_correlation_sections(
    correlations: list[dict[str, Any]],
    unified_correlations: dict[str, Any],
    limit: int = 2,
) -> list[dict[str, Any]]:
    lookup = _correlation_lookup(unified_correlations)
    enriched: list[dict[str, Any]] = []

    for item in correlations:
        if not isinstance(item, dict):
            continue
        label = str(item.get("correlation") or item.get("comparison") or "").strip()
        if not label:
            continue

        match = lookup.get(_normalize_label(label), {})
        if not isinstance(match, dict):
            match = {}

        strength = str(item.get("strength") or match.get("strength") or "weak").lower()
        if strength not in {"weak", "moderate", "strong"}:
            strength = "weak"

        confidence = str(item.get("confidence") or match.get("confidence") or "low").lower()
        if confidence not in {"low", "medium", "high"}:
            confidence = "low"

        confidence_score = _coerce_float(item.get("confidence_score"))
        if confidence_score is None:
            confidence_score = _coerce_float(match.get("confidence_score"))
        importance_score = _coerce_float(item.get("importance_score"))
        if importance_score is None:
            importance_score = _coerce_float(match.get("importance_score"))

        interpretation = _clean_interpretation_text(str(item.get("interpretation") or "").strip())
        if not interpretation:
            interpretation = _clean_interpretation_text(str(match.get("interpretation") or "").strip())
        if not interpretation:
            direction = str(match.get("direction") or "neutral")
            if direction == "positive":
                interpretation = "This comparison aligned with a favorable outcome."
            elif direction == "negative":
                interpretation = "This comparison aligned with a less favorable outcome."
            else:
                interpretation = "This comparison showed little measurable difference."

        raw_sample = item.get("sample_size")
        if not isinstance(raw_sample, dict):
            raw_sample = match.get("sample_size")
        sample_size = raw_sample if isinstance(raw_sample, dict) else {}
        group_a_n = int(sample_size.get("group_a") or 0) if isinstance(sample_size, dict) else 0
        group_b_n = int(sample_size.get("group_b") or 0) if isinstance(sample_size, dict) else 0
        control_level = str(item.get("control_level") or match.get("control_level") or "semi_controllable").lower()
        if control_level not in {"controllable", "semi_controllable", "uncontrollable"}:
            control_level = "semi_controllable"

        enriched.append(
            {
                "correlation": label,
                "strength": strength,
                "confidence": confidence,
                "control_level": control_level,
                "sample_size": {"group_a": group_a_n, "group_b": group_b_n},
                "interpretation": interpretation,
                **({"confidence_score": confidence_score} if confidence_score is not None else {}),
                **({"importance_score": importance_score} if importance_score is not None else {}),
            }
        )
        if len(enriched) >= limit:
            break

    return enriched


def _fmt_signed(value: float | None, precision: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.{precision}f}"


def _clean_interpretation_text(text_value: str) -> str:
    text_value = " ".join(str(text_value or "").split())
    if not text_value:
        return ""
    text_value = re.sub(r"\s*Confidence\s*(?:is|:)\s*[^.]+\.?", "", text_value, flags=re.IGNORECASE)
    text_value = re.sub(r"\s+", " ", text_value).strip()
    return text_value


def _driver_label_from_correlation(key: str, category: str, comparison: str) -> str:
    key_map = {
        "workout_same_day_mood": "Workout presence",
        "prev_workout_next_day_mood": "Workout carryover into next-day mood",
        "prev_alcohol_next_day_mood": "Alcohol impact on next-day mood",
        "high_calorie_same_day_mood": "High-calorie days",
        "workout_same_day_systolic": "Workout effect on systolic BP",
        "workout_same_day_diastolic": "Workout effect on diastolic BP",
        "prev_workout_next_day_systolic": "Workout carryover into next-day systolic BP",
        "prev_workout_next_day_diastolic": "Workout carryover into next-day diastolic BP",
        "prev_alcohol_next_day_systolic": "Alcohol impact on next-day systolic BP",
        "prev_alcohol_next_day_diastolic": "Alcohol impact on next-day diastolic BP",
        "high_calorie_same_day_systolic": "High-calorie days and systolic BP",
        "high_calorie_same_day_diastolic": "High-calorie days and diastolic BP",
        "rainy_same_day_mood": "Rainy days",
        "cloudy_same_day_mood": "Cloudy days",
        "sunny_same_day_mood": "Sunny days",
        "cold_vs_mild_mood": "Cold vs mild weather",
        "rainy_same_day_systolic": "Rainy days and systolic BP",
        "rainy_same_day_diastolic": "Rainy days and diastolic BP",
        "cloudy_same_day_systolic": "Cloudy days and systolic BP",
        "cloudy_same_day_diastolic": "Cloudy days and diastolic BP",
        "sunny_same_day_systolic": "Sunny days and systolic BP",
        "sunny_same_day_diastolic": "Sunny days and diastolic BP",
        "cold_vs_mild_systolic": "Cold vs mild weather and systolic BP",
        "cold_vs_mild_diastolic": "Cold vs mild weather and diastolic BP",
        "no_weed_vs_weed_same_day_mood": "No-weed days vs weed days mood",
        "no_weed_vs_weed_next_day_mood": "Next-day mood after no-weed vs weed",
        "no_weed_vs_weed_same_day_systolic": "No-weed days vs weed days systolic BP",
        "no_weed_vs_weed_same_day_diastolic": "No-weed days vs weed days diastolic BP",
        "no_weed_vs_weed_next_day_systolic": "Next-day systolic BP after no-weed vs weed",
        "no_weed_vs_weed_next_day_diastolic": "Next-day diastolic BP after no-weed vs weed",
    }
    if key in key_map:
        return key_map[key]

    if category.startswith("weather_"):
        return "Weather relationship"
    if category.startswith("behavior_"):
        return "Behavior relationship"
    if category.startswith("substance_"):
        return "No-weed vs weed relationship"
    return comparison or "Structured driver"


def _fallback_top_drivers(
    aggregated_journal_analysis: dict[str, Any],
    weekly_behavior_metrics: dict[str, Any],
    unified_correlations: dict[str, Any],
) -> list[dict[str, str]]:
    drivers: list[dict[str, str]] = []

    selected_correlations = _prioritized_correlation_candidates(unified_correlations, limit=2)

    for correlation in selected_correlations:
        if not isinstance(correlation, dict):
            continue
        key = str(correlation.get("key") or "")
        category = str(correlation.get("category") or "")
        comparison = str(correlation.get("comparison") or correlation.get("correlation") or "").strip()
        evidence = correlation.get("evidence") or {}
        delta = _coerce_float(correlation.get("delta"))
        confidence = str(correlation.get("confidence") or "low")
        group_a_label = str(evidence.get("group_a_label") or "group A")
        group_b_label = str(evidence.get("group_b_label") or "group B")
        group_a_avg = _coerce_float(evidence.get("group_a_avg"))
        group_b_avg = _coerce_float(evidence.get("group_b_avg"))
        sample_size = correlation.get("sample_size") or {}
        group_a_n = int(sample_size.get("group_a") or 0) if isinstance(sample_size, dict) else 0
        group_b_n = int(sample_size.get("group_b") or 0) if isinstance(sample_size, dict) else 0
        direction = str(correlation.get("direction") or "neutral")

        if comparison:
            if direction == "positive":
                signal = "more favorable"
            elif direction == "negative":
                signal = "less favorable"
            else:
                signal = "similar"
            drivers.append(
                {
                    "driver": _driver_label_from_correlation(key, category, comparison),
                    "evidence": (
                        f"{comparison}: {group_a_label} {_fmt_signed(group_a_avg)} vs "
                        f"{group_b_label} {_fmt_signed(group_b_avg)} "
                        f"(delta {_fmt_signed(delta)}, {signal}; confidence {confidence}, n={group_a_n} vs n={group_b_n})."
                    ),
                }
            )

    top_stressors = aggregated_journal_analysis.get("top_stressors") or []
    if isinstance(top_stressors, list) and top_stressors:
        top_stressor = top_stressors[0]
        if isinstance(top_stressor, dict):
            label = str(top_stressor.get("label") or "").strip()
            count = int(top_stressor.get("count") or 0)
            if label:
                drivers.append(
                    {
                        "driver": f"Recurring stressor: {label}",
                        "evidence": f"Appeared in {count} analyzed entries.",
                    }
                )

    top_motivation = aggregated_journal_analysis.get("top_motivation_drivers") or []
    if isinstance(top_motivation, list) and top_motivation:
        motivator = top_motivation[0]
        if isinstance(motivator, dict):
            label = str(motivator.get("label") or "").strip()
            count = int(motivator.get("count") or 0)
            if label:
                drivers.append(
                    {
                        "driver": f"Motivation signal: {label}",
                        "evidence": f"Repeated {count} times in positive/life-direction signals.",
                    }
                )

    mood_trend = aggregated_journal_analysis.get("mood_trend") or {}
    if isinstance(mood_trend, dict):
        direction = str(mood_trend.get("direction") or "")
        delta = _coerce_float(mood_trend.get("delta"))
        if direction in {"up", "down", "flat"} and delta is not None:
            drivers.append(
                {
                    "driver": "Weekly mood trajectory",
                    "evidence": f"Mood trend moved {direction} by {_fmt_signed(delta)} across analyzed entries.",
                }
            )

    return _merge_driver_sections([], drivers, limit=3)


def _fallback_correlation_sections(unified_correlations: dict[str, Any]) -> list[dict[str, Any]]:
    fallback: list[dict[str, Any]] = []
    for correlation in _prioritized_correlation_candidates(unified_correlations, limit=2):
        if not isinstance(correlation, dict):
            continue
        strength = str(correlation.get("strength") or "weak")
        label = str(correlation.get("comparison") or correlation.get("correlation") or "").strip()
        confidence = str(correlation.get("confidence") or "low")
        interpretation = _clean_interpretation_text(str(correlation.get("interpretation") or "").strip())
        sample_size = correlation.get("sample_size") or {}
        if not label:
            continue

        if not interpretation:
            direction = str(correlation.get("direction") or "neutral")
            if direction == "positive":
                interpretation = "This comparison aligned with a favorable outcome."
            elif direction == "negative":
                interpretation = "This comparison aligned with a less favorable outcome."
            else:
                interpretation = "This comparison showed little measurable difference."

        fallback.append(
            {
                "correlation": label,
                "strength": strength if strength in {"weak", "moderate", "strong"} else "weak",
                "interpretation": interpretation,
                "confidence": confidence if confidence in {"low", "medium", "high"} else "low",
                "confidence_score": _coerce_float(correlation.get("confidence_score")) or 0.0,
                "control_level": str(correlation.get("control_level") or "semi_controllable"),
                "importance_score": _coerce_float(correlation.get("importance_score")) or 0.0,
                "sample_size": {
                    "group_a": int(sample_size.get("group_a") or 0) if isinstance(sample_size, dict) else 0,
                    "group_b": int(sample_size.get("group_b") or 0) if isinstance(sample_size, dict) else 0,
                },
            }
        )

    return _merge_correlation_sections([], fallback, limit=2)


def _fallback_pattern_sections(
    aggregated_journal_analysis: dict[str, Any],
    unified_correlations: dict[str, Any],
) -> list[str]:
    patterns: list[str] = []
    mood_trend = aggregated_journal_analysis.get("mood_trend") or {}
    if isinstance(mood_trend, dict):
        direction = str(mood_trend.get("direction") or "")
        delta = _coerce_float(mood_trend.get("delta"))
        if direction in {"up", "down", "flat"} and delta is not None:
            patterns.append(f"Mood trend was {direction} ({_fmt_signed(delta)} delta across analyzed entries).")

    repeated_themes = aggregated_journal_analysis.get("notable_repeated_themes") or []
    if isinstance(repeated_themes, list):
        for theme in repeated_themes[:2]:
            if not isinstance(theme, dict):
                continue
            label = str(theme.get("theme") or "").strip()
            count = int(theme.get("count") or 0)
            if label and count >= 2:
                patterns.append(f"Theme loop: {label} repeated {count} times.")

    for correlation in (unified_correlations.get("strongest_correlations") or [])[:2]:
        if not isinstance(correlation, dict):
            continue
        confidence = str(correlation.get("confidence") or "low")
        if confidence not in {"medium", "high"}:
            continue
        direction = str(correlation.get("direction") or "neutral")
        label = str(correlation.get("comparison") or correlation.get("correlation") or "").strip()
        if not label:
            continue
        patterns.append(
            f"{label} showed a {direction} signal with {confidence} confidence."
        )

    return _merge_string_sections([], patterns, limit=4)


def _fallback_risk_flags(
    aggregated_journal_analysis: dict[str, Any],
    unified_correlations: dict[str, Any],
) -> list[str]:
    risks: list[str] = []
    high_stress_ratio = _coerce_float(aggregated_journal_analysis.get("high_stress_entry_ratio")) or 0.0
    if high_stress_ratio >= 0.4:
        risks.append(f"High-stress entries were {round(high_stress_ratio * 100)}% of analyzed entries.")

    mood_trend = aggregated_journal_analysis.get("mood_trend") or {}
    if isinstance(mood_trend, dict):
        direction = str(mood_trend.get("direction") or "")
        delta = _coerce_float(mood_trend.get("delta")) or 0.0
        if direction == "down" and delta <= -0.5:
            risks.append(f"Mood trended downward by {_fmt_signed(delta)} across the week.")

    top_stressors = aggregated_journal_analysis.get("top_stressors") or []
    if isinstance(top_stressors, list) and top_stressors:
        top_stressor = top_stressors[0]
        if isinstance(top_stressor, dict):
            label = str(top_stressor.get("label") or "").strip()
            count = int(top_stressor.get("count") or 0)
            if label and count >= 3:
                risks.append(f"Recurring stressor '{label}' appeared {count} times.")

    for correlation in (unified_correlations.get("strongest_correlations") or [])[:3]:
        if not isinstance(correlation, dict):
            continue
        direction = str(correlation.get("direction") or "neutral")
        confidence = str(correlation.get("confidence") or "low")
        if direction != "negative" or confidence == "low":
            continue

        label = str(correlation.get("comparison") or correlation.get("correlation") or "").strip()
        if label:
            risks.append(f"{label} was unfavorable ({confidence} confidence).")

    return _merge_string_sections([], risks, limit=4)


def _fallback_recommendations(
    aggregated_journal_analysis: dict[str, Any],
    unified_correlations: dict[str, Any],
) -> list[str]:
    recommendations: list[str] = []
    seen: set[str] = set()

    def _add_recommendation(text_value: str):
        normalized = _normalize_label(text_value)
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        recommendations.append(text_value)

    all_correlations = [
        item
        for item in (unified_correlations.get("all_correlations") or [])
        if isinstance(item, dict)
    ]
    reliable_correlations = [
        item
        for item in all_correlations
        if str(item.get("confidence") or "").lower() in {"medium", "high"}
        and str(item.get("control_level") or "").lower() == "controllable"
    ]

    for correlation in reliable_correlations[:8]:
        key = str(correlation.get("key") or "")
        direction = str(correlation.get("direction") or "neutral")
        confidence = str(correlation.get("confidence") or "low")

        if key.startswith("workout_") or key.startswith("prev_workout_"):
            if direction == "positive":
                _add_recommendation(
                    f"Protect at least 3 workout slots next week; this signal is {confidence}-confidence."
                )
            continue

        if key.startswith("high_calorie_same_day_"):
            if direction == "negative":
                _add_recommendation(
                    "Reduce high-calorie spikes by planning steadier meal totals across the week."
                )
            continue

        if key.startswith("prev_alcohol_next_day_"):
            if direction == "negative":
                _add_recommendation(
                    "Limit alcohol on nights before important days and track next-day mood/BP outcomes."
                )
            continue

        if key.startswith("no_weed_vs_weed_next_day_"):
            if direction == "positive":
                _add_recommendation(
                    "Schedule intentional no-weed evenings before priority mornings and track next-day mood/BP."
                )
            continue

        if key.startswith("no_weed_vs_weed_same_day_"):
            if direction == "positive":
                _add_recommendation(
                    "Increase planned no-weed days this week and compare same-day mood/BP results."
                )
            continue

        if key.startswith("rainy_same_day_") or key.startswith("cloudy_same_day_"):
            if direction == "negative":
                _add_recommendation(
                    "On rainy/cloudy days, pre-schedule an indoor movement and decompression block."
                )
            continue

    high_stress_ratio = _coerce_float(aggregated_journal_analysis.get("high_stress_entry_ratio")) or 0.0
    if high_stress_ratio >= 0.4:
        _add_recommendation("Add a fixed 20-minute decompression block on high-pressure days.")

    top_stressors = aggregated_journal_analysis.get("top_stressors") or []
    if isinstance(top_stressors, list) and top_stressors:
        top_stressor = top_stressors[0]
        if isinstance(top_stressor, dict):
            label = str(top_stressor.get("label") or "").strip()
            count = int(top_stressor.get("count") or 0)
            if label and count >= 3:
                _add_recommendation(
                    f"Create one concrete mitigation step for recurring stressor '{label}' before it escalates."
                )

    if len(recommendations) < 3 and reliable_correlations:
        top_controllable_label = str(reliable_correlations[0].get("comparison") or "").strip()
        _add_recommendation(
            (
                f"Run a 7-day experiment focused on '{top_controllable_label}' and review outcomes at week end."
                if top_controllable_label
                else "Run a 7-day experiment on your top controllable driver and review outcomes at week end."
            )
        )
    if len(recommendations) < 3:
        _add_recommendation(
            "Keep workout/calorie/alcohol/safety-meeting logs complete so controllable drivers stay decision-ready."
        )

    return recommendations[:3]


def _has_usable_weekly_signal(
    weekly_behavior_metrics: dict[str, Any],
    aggregated_journal_analysis: dict[str, Any],
    unified_correlations: dict[str, Any],
) -> bool:
    strongest = unified_correlations.get("strongest_correlations") or []
    if isinstance(strongest, list) and any(isinstance(item, dict) for item in strongest):
        return True

    top_stressors = aggregated_journal_analysis.get("top_stressors") or []
    top_motivation = aggregated_journal_analysis.get("top_motivation_drivers") or []
    repeated = aggregated_journal_analysis.get("notable_repeated_themes") or []
    if any(isinstance(group, list) and len(group) > 0 for group in [top_stressors, top_motivation, repeated]):
        return True

    mood_trend = aggregated_journal_analysis.get("mood_trend") or {}
    delta = _coerce_float(mood_trend.get("delta")) if isinstance(mood_trend, dict) else None
    if delta is not None and abs(delta) >= 0.3:
        return True

    metrics = weekly_behavior_metrics.get("metrics") if isinstance(weekly_behavior_metrics, dict) else None
    if isinstance(metrics, dict):
        days_with_data = int(metrics.get("days_with_data") or 0)
        journal_count = int(metrics.get("journal_count") or 0)
        if days_with_data >= 4 or journal_count >= 3:
            return True

    return False


def _is_limited_signal_text(text_value: str) -> bool:
    normalized = _normalize_label(text_value)
    if not normalized:
        return True
    return any(
        phrase in normalized
        for phrase in [
            "structured signal is limited",
            "signal is limited this week",
            "not enough structured evidence",
            "insufficient signal",
        ]
    )


def _fallback_system_state(
    weekly_behavior_metrics: dict[str, Any],
    aggregated_journal_analysis: dict[str, Any],
    unified_correlations: dict[str, Any],
) -> str:
    avg_mood = _coerce_float(aggregated_journal_analysis.get("average_mood_score"))
    high_stress_ratio = _coerce_float(aggregated_journal_analysis.get("high_stress_entry_ratio"))

    line_1_bits: list[str] = []
    if avg_mood is not None:
        line_1_bits.append(f"Average mood was {_fmt_signed(avg_mood)}")
    if high_stress_ratio is not None:
        line_1_bits.append(f"high-stress entries were {round(high_stress_ratio * 100)}%")
    line_1 = "; ".join(line_1_bits).strip()
    if not line_1:
        line_1 = "Unified analytics signal was strong enough to identify drivers and risks."

    top = _primary_correlation_for_system_state(unified_correlations)
    line_2 = ""
    if isinstance(top, dict):
        label = str(top.get("comparison") or top.get("correlation") or "").strip()
        delta = _coerce_float(top.get("delta"))
        confidence = str(top.get("confidence") or "").strip()
        control_level = str(top.get("control_level") or "").strip().lower()
        if label:
            control_hint = f", {control_level}" if control_level in {"controllable", "semi_controllable", "uncontrollable"} else ""
            confidence_suffix = f", confidence {confidence}" if confidence else ""
            line_2 = f"Strongest relationship: {label} (delta {_fmt_signed(delta)}{confidence_suffix}{control_hint})."

    if line_2:
        return f"{line_1}. {line_2}"
    return f"{line_1}."


def _build_weekly_sections_with_fallback(
    llm_structured: dict[str, Any],
    weekly_behavior_metrics: dict[str, Any],
    aggregated_journal_analysis: dict[str, Any],
    unified_correlations: dict[str, Any],
) -> dict[str, Any]:
    llm_top_drivers = _sanitize_top_drivers(llm_structured.get("top_drivers"))
    llm_correlations = _sanitize_correlations(llm_structured.get("correlations"))
    llm_patterns = _sanitize_string_list(llm_structured.get("patterns"))
    llm_risk_flags = _sanitize_string_list(llm_structured.get("risk_flags"))
    llm_recommendations = _sanitize_string_list(llm_structured.get("recommendations"))
    llm_key_insights = _sanitize_string_list(llm_structured.get("key_insights"))
    llm_what_to_focus_on = _sanitize_string_list(llm_structured.get("what_to_focus_on"))
    llm_system_state = str(llm_structured.get("system_state") or "").strip()

    fallback_top_drivers = _fallback_top_drivers(aggregated_journal_analysis, weekly_behavior_metrics, unified_correlations)
    fallback_correlations = _fallback_correlation_sections(unified_correlations)
    fallback_patterns = _fallback_pattern_sections(aggregated_journal_analysis, unified_correlations)
    fallback_risk_flags = _fallback_risk_flags(aggregated_journal_analysis, unified_correlations)
    fallback_recommendations = _fallback_recommendations(aggregated_journal_analysis, unified_correlations)

    # Prefer deterministic structured sections first for trustworthiness.
    top_drivers = _merge_driver_sections(fallback_top_drivers, llm_top_drivers, limit=3)
    correlations = _merge_correlation_sections(fallback_correlations, llm_correlations, limit=2)
    correlations = _enrich_correlation_sections(correlations, unified_correlations, limit=2)
    patterns = _merge_string_sections(llm_patterns, fallback_patterns, limit=4)
    risk_flags = _merge_string_sections(llm_risk_flags, fallback_risk_flags, limit=4)
    recommendations = _merge_string_sections(fallback_recommendations, llm_recommendations, limit=3)

    usable_signal = _has_usable_weekly_signal(
        weekly_behavior_metrics=weekly_behavior_metrics,
        aggregated_journal_analysis=aggregated_journal_analysis,
        unified_correlations=unified_correlations,
    )

    if llm_system_state and not (_is_limited_signal_text(llm_system_state) and usable_signal):
        system_state = llm_system_state
    elif usable_signal:
        system_state = _fallback_system_state(
            weekly_behavior_metrics=weekly_behavior_metrics,
            aggregated_journal_analysis=aggregated_journal_analysis,
            unified_correlations=unified_correlations,
        )
    else:
        system_state = "Structured signal is limited for this week."

    evidence_quality = str(llm_structured.get("evidence_quality") or "").strip()
    if not evidence_quality:
        evidence_quality = str(unified_correlations.get("evidence_quality") or "").strip()
    if usable_signal and evidence_quality == "limited":
        evidence_quality = "usable"
    if not evidence_quality:
        evidence_quality = "usable" if usable_signal else "limited"

    fallback_key_insights = _build_key_insights(
        top_drivers=top_drivers,
        correlation_items=correlations,
        risk_flags=risk_flags,
        recommendations=recommendations,
        system_state=system_state,
    )
    fallback_what_to_focus_on = _build_what_to_focus_on(
        top_drivers=top_drivers,
        correlation_items=correlations,
        risk_flags=risk_flags,
        recommendations=recommendations,
    )
    key_insights = _merge_string_sections(llm_key_insights, fallback_key_insights, limit=4)
    what_to_focus_on = _merge_string_sections(llm_what_to_focus_on, fallback_what_to_focus_on, limit=3)

    return {
        "system_state": system_state,
        "top_drivers": top_drivers,
        "correlations": correlations,
        "patterns": patterns,
        "risk_flags": risk_flags,
        "recommendations": recommendations,
        "key_insights": key_insights,
        "what_to_focus_on": what_to_focus_on,
        "evidence_quality": evidence_quality,
    }


def _month_bounds(anchor_date: date) -> tuple[date, date]:
    period_start = anchor_date.replace(day=1)
    if period_start.month == 12:
        next_month_start = date(period_start.year + 1, 1, 1)
    else:
        next_month_start = date(period_start.year, period_start.month + 1, 1)
    period_end = next_month_start - timedelta(days=1)
    return period_start, period_end


def _latest_analyzed_entry_date(db: Session) -> date | None:
    return (
        db.query(Journal.entry_date)
        .join(JournalEntryAnalysis, JournalEntryAnalysis.journal_entry_id == Journal.id)
        .order_by(Journal.entry_date.desc(), Journal.id.desc())
        .limit(1)
        .scalar()
    )


def _resolve_monthly_window(payload: JournalWeeklyPeriodRequest | None) -> tuple[date, date]:
    if payload and payload.period_start and payload.period_end:
        return payload.period_start, payload.period_end

    return _month_bounds(date.today())

@router.post("/weekly")
def create_weekly_insight(db: Session = Depends(get_db)):
    period_end = date.today()
    period_start = period_end - timedelta(days=6)

    metrics_sql = text("""
        WITH daily_calories AS (
            SELECT
                log_date,
                SUM(calories) AS total_calories,
                MAX(
                    CASE WHEN meal = 'drink' AND food ILIKE 'beer%' THEN 1 ELSE 0 END
                ) AS had_alcohol
            FROM diet
            WHERE log_date BETWEEN :period_start AND :period_end
            GROUP BY log_date
        ),
        weight_stats AS (
            SELECT
                MIN(weight) FILTER (WHERE entry_date = :period_start) AS start_weight,
                MIN(weight) FILTER (WHERE entry_date = :period_end) AS end_weight,
                AVG(weight) AS avg_weight
            FROM weight
            WHERE entry_date BETWEEN :period_start AND :period_end
        ),
        bp_stats AS (
            SELECT
                AVG(systolic) AS avg_systolic,
                AVG(diastolic) AS avg_diastolic
            FROM blood_pressure
            WHERE entry_date BETWEEN :period_start AND :period_end
        )
        SELECT json_build_object(
            'period_start', :period_start,
            'period_end', :period_end,
            'avg_daily_calories', (
                SELECT ROUND(AVG(total_calories)::numeric, 1) FROM daily_calories
            ),
            'alcohol_days', (
                SELECT COALESCE(SUM(had_alcohol), 0) FROM daily_calories
            ),
            'start_weight', (SELECT start_weight FROM weight_stats),
            'end_weight', (SELECT end_weight FROM weight_stats),
            'avg_weight', (SELECT ROUND(avg_weight::numeric, 1) FROM weight_stats),
            'avg_systolic', (SELECT ROUND(avg_systolic::numeric, 1) FROM bp_stats),
            'avg_diastolic', (SELECT ROUND(avg_diastolic::numeric, 1) FROM bp_stats)
        ) AS metrics
    """)

    row = db.execute(
        metrics_sql,
        {"period_start": period_start, "period_end": period_end},
    ).fetchone()

    metrics = row.metrics if row and row.metrics else {}
    insight_text = generate_weekly_report(metrics)

    insert_sql = text("""
        INSERT INTO ai_insights (
            insight_type,
            insight_date,
            period_start,
            period_end,
            category,
            model_provider,
            model_name,
            prompt_version,
            input_payload,
            insight_text,
            status
        )
        VALUES (
            'weekly_report',
            CURRENT_DATE,
            :period_start,
            :period_end,
            'health',
            'ollama',
            'gemma3:4b',
            'v1',
            CAST(:input_payload AS jsonb),
            :insight_text,
            'complete'
        )
        RETURNING id, insight_text
    """)

    result = db.execute(
        insert_sql,
        {
            "period_start": period_start,
            "period_end": period_end,
            "input_payload": json.dumps(metrics, default=str),
            "insight_text": insight_text,
        },
    ).fetchone()

    db.commit()

    return {
        "id": result.id,
        "period_start": str(period_start),
        "period_end": str(period_end),
        "insight_text": result.insight_text,
        "metrics": metrics,
    }


@router.post("/journal/weekly-profile", response_model=JournalPatternProfileOut)
def create_weekly_journal_profile(
    payload: JournalWeeklyPeriodRequest | None = None,
    db: Session = Depends(get_db),
):
    period_start, period_end = _resolve_weekly_window(payload)

    rows = _load_weekly_analysis_rows(db, period_start, period_end)

    if not rows:
        latest_entry_date = _latest_analyzed_entry_date(db)

        if latest_entry_date is None:
            raise HTTPException(status_code=404, detail="No analyzed journal entries exist yet.")

        period_end = latest_entry_date
        period_start = period_end - timedelta(days=6)
        rows = _load_weekly_analysis_rows(db, period_start, period_end)

        if not rows:
            if payload and payload.period_start and payload.period_end:
                raise HTTPException(status_code=404, detail="No journal analyses found for the requested period.")

    analyses = []
    mood_scores = []

    for analysis, journal in rows:
        analyses.append(
            {
                "journal_entry_id": analysis.journal_entry_id,
                "entry_date": str(journal.entry_date),
                "mood_score": float(analysis.mood_score) if analysis.mood_score is not None else None,
                "emotional_tone": analysis.emotional_tone,
                "key_emotions": analysis.key_emotions or [],
                "stressors": analysis.stressors or [],
                "positive_signals": analysis.positive_signals or [],
                "thinking_patterns": analysis.thinking_patterns or [],
                "life_direction_signals": analysis.life_direction_signals or [],
                "insight": analysis.insight,
                "reflection_questions": analysis.reflection_questions or [],
                "encouragement": analysis.encouragement,
            }
        )
        if analysis.mood_score is not None:
            mood_scores.append(float(analysis.mood_score))

    structured = build_journal_pattern_profile(
        analyses=analyses,
        period_type="weekly",
        period_start=str(period_start),
        period_end=str(period_end),
    )

    average_mood_score = (
        round(sum(mood_scores) / len(mood_scores), 2) if mood_scores else structured.get("average_mood_score")
    )

    profile = JournalPatternProfile(
        period_type="weekly",
        period_start=period_start,
        period_end=period_end,
        entry_count=len(rows),
        model_provider="anthropic",
        model_name="claude-haiku-4-5",
        prompt_version="v2",
        average_mood_score=average_mood_score,
        dominant_emotions=structured.get("dominant_emotions", []),
        recurring_stressors=structured.get("recurring_stressors", []),
        recurring_positive_signals=structured.get("recurring_positive_signals", []),
        recurring_thinking_patterns=structured.get("recurring_thinking_patterns", []),
        recurring_life_direction_signals=structured.get("recurring_life_direction_signals", []),
        core_values=structured.get("core_values", []),
        motivation_drivers=structured.get("motivation_drivers", []),
        growth_signals=structured.get("growth_signals", []),
        risk_signals=structured.get("risk_signals", []),
        pattern_summary=structured.get("pattern_summary"),
        raw_output=structured,
    )

    db.add(profile)

    db.execute(
        text("""
            INSERT INTO ai_insights (
                insight_type,
                insight_date,
                period_start,
                period_end,
                category,
                model_provider,
                model_name,
                prompt_version,
                input_payload,
                insight_text,
                structured_output,
                status
            )
            VALUES (
                'pattern_detection',
                CURRENT_DATE,
                :period_start,
                :period_end,
                'journal',
                'anthropic',
                'claude-haiku-4-5',
                'v2',
                CAST(:input_payload AS jsonb),
                :insight_text,
                CAST(:structured_output AS jsonb),
                'complete'
            )
        """),
        {
            "period_start": period_start,
            "period_end": period_end,
            "input_payload": json.dumps({"entry_count": len(rows), "analyses": analyses}, default=str),
            "insight_text": structured.get("pattern_summary", ""),
            "structured_output": json.dumps(structured, default=str),
        },
    )

    db.commit()
    db.refresh(profile)
    return profile


@router.post("/journal/monthly-profile", response_model=JournalPatternProfileOut)
def create_monthly_journal_profile(
    payload: JournalWeeklyPeriodRequest | None = None,
    db: Session = Depends(get_db),
):
    period_start, period_end = _resolve_monthly_window(payload)
    rows = _load_weekly_analysis_rows(db, period_start, period_end)

    if not rows:
        latest_entry_date = _latest_analyzed_entry_date(db)
        if latest_entry_date is None:
            raise HTTPException(status_code=404, detail="No analyzed journal entries exist yet.")

        if payload and payload.period_start and payload.period_end:
            raise HTTPException(status_code=404, detail="No journal analyses found for the requested period.")

        period_start, period_end = _month_bounds(latest_entry_date)
        rows = _load_weekly_analysis_rows(db, period_start, period_end)
        if not rows:
            raise HTTPException(status_code=404, detail="No journal analyses found for any month.")

    existing = (
        db.query(JournalPatternProfile)
        .filter(
            JournalPatternProfile.period_type == "monthly",
            JournalPatternProfile.period_start == period_start,
            JournalPatternProfile.period_end == period_end,
        )
        .order_by(JournalPatternProfile.created_at.desc())
        .first()
    )
    if existing:
        return existing

    analyses, journal_ids, average_mood_score = _serialize_weekly_analyses(rows)

    structured = build_journal_pattern_profile(
        analyses=analyses,
        period_type="monthly",
        period_start=str(period_start),
        period_end=str(period_end),
    )

    if average_mood_score is None:
        average_mood_score = structured.get("average_mood_score")

    profile = JournalPatternProfile(
        period_type="monthly",
        period_start=period_start,
        period_end=period_end,
        entry_count=len(rows),
        model_provider="anthropic",
        model_name="claude-haiku-4-5",
        prompt_version="v3-monthly-from-journal-analyses",
        average_mood_score=average_mood_score,
        dominant_emotions=structured.get("dominant_emotions", []),
        recurring_stressors=structured.get("recurring_stressors", []),
        recurring_positive_signals=structured.get("recurring_positive_signals", []),
        recurring_thinking_patterns=structured.get("recurring_thinking_patterns", []),
        recurring_life_direction_signals=structured.get("recurring_life_direction_signals", []),
        core_values=structured.get("core_values", []),
        motivation_drivers=structured.get("motivation_drivers", []),
        growth_signals=structured.get("growth_signals", []),
        risk_signals=structured.get("risk_signals", []),
        pattern_summary=structured.get("pattern_summary"),
        raw_output={
            **structured,
            "source_type": "journal_analyses",
            "source_entry_count": len(rows),
            "source_journal_ids": journal_ids,
        },
    )
    db.add(profile)

    db.execute(
        text("""
            INSERT INTO ai_insights (
                insight_type,
                insight_date,
                period_start,
                period_end,
                period_type,
                category,
                model_provider,
                model_name,
                prompt_version,
                input_payload,
                insight_text,
                structured_output,
                status
            )
            VALUES (
                'pattern_detection',
                CURRENT_DATE,
                :period_start,
                :period_end,
                'monthly',
                'journal',
                'anthropic',
                'claude-haiku-4-5',
                'v3-monthly-from-journal-analyses',
                CAST(:input_payload AS jsonb),
                :insight_text,
                CAST(:structured_output AS jsonb),
                'complete'
            )
        """),
        {
            "period_start": period_start,
            "period_end": period_end,
            "input_payload": json.dumps(
                {
                    "period_type": "monthly",
                    "source_type": "journal_analyses",
                    "entry_count": len(rows),
                    "journal_ids": journal_ids,
                    "average_mood_score": average_mood_score,
                    "analyses": analyses,
                },
                default=str,
            ),
            "insight_text": structured.get("pattern_summary", ""),
            "structured_output": json.dumps(structured, default=str),
        },
    )

    db.commit()
    db.refresh(profile)
    return profile


@router.post("/journal/weekly-summary")
def create_weekly_journal_summary(
    payload: JournalWeeklyPeriodRequest | None = None,
    db: Session = Depends(get_db),
):
    period_start, period_end = _resolve_weekly_window(payload)

    rows = _load_weekly_analysis_rows(db, period_start, period_end)

    if not rows:
        latest_entry_date = _latest_analyzed_entry_date(db)

        if latest_entry_date is None:
            raise HTTPException(status_code=404, detail="No analyzed journal entries exist yet.")

        period_end = latest_entry_date
        period_start = period_end - timedelta(days=6)
        rows = _load_weekly_analysis_rows(db, period_start, period_end)

        if not rows:
            if payload and payload.period_start and payload.period_end:
                raise HTTPException(status_code=404, detail="No journal analyses found for the requested period.")

    analyses, journal_ids, average_mood_score = _serialize_weekly_analyses(rows)

    existing = db.execute(
        text(
            """
            SELECT id, insight_type, period_start, period_end, insight_text, structured_output, created_at, prompt_version
            FROM ai_insights
            WHERE category = 'journal'
              AND insight_type = 'journal_weekly_summary'
              AND period_start = :period_start
              AND period_end = :period_end
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"period_start": period_start, "period_end": period_end},
    ).fetchone()

    if (
        existing
        and existing.prompt_version == WEEKLY_BEHAVIORAL_PROMPT_VERSION
        and _is_current_weekly_behavior_format(existing.structured_output)
        and _has_populated_weekly_sections(existing.structured_output)
    ):
        return {
            "id": existing.id,
            "insight_type": existing.insight_type,
            "period_start": str(existing.period_start),
            "period_end": str(existing.period_end),
            "insight_text": existing.insight_text,
            "structured_output": existing.structured_output,
            "created_at": existing.created_at,
            "entry_count": len(rows),
            "journal_ids": journal_ids,
            "average_mood_score": average_mood_score,
        }

    weekly_behavior_metrics = _load_weekly_behavior_metrics(db, period_start, period_end)
    aggregated_journal_analysis = aggregate_weekly_journal_analysis(analyses)
    normalized_daily_rows = build_normalized_daily_rows(db, period_start, period_end)
    unified_correlations = compute_unified_correlations(normalized_daily_rows)
    behavior_correlations = {
        "candidate_count": len(unified_correlations.get("behavior_correlations") or []),
        "strongest_correlations": (unified_correlations.get("behavior_correlations") or [])[:2],
        "all_correlations": unified_correlations.get("behavior_correlations") or [],
        "evidence_quality": unified_correlations.get("evidence_quality") or "limited",
    }
    input_payload = build_weekly_insight_payload(
        weekly_behavior_metrics=weekly_behavior_metrics,
        aggregated_journal_analysis=aggregated_journal_analysis,
        unified_correlations=unified_correlations,
    )

    llm_structured = build_weekly_behavioral_insight(input_payload)
    resolved_sections = _build_weekly_sections_with_fallback(
        llm_structured=llm_structured,
        weekly_behavior_metrics=weekly_behavior_metrics,
        aggregated_journal_analysis=aggregated_journal_analysis,
        unified_correlations=unified_correlations,
    )

    # Keep "summary"/"themes" for frontend compatibility while storing richer structured sections.
    structured_output = {
        "system_state": resolved_sections["system_state"],
        "top_drivers": resolved_sections["top_drivers"],
        "correlations": resolved_sections["correlations"],
        "patterns": resolved_sections["patterns"],
        "risk_flags": resolved_sections["risk_flags"],
        "recommendations": resolved_sections["recommendations"],
        "key_insights": resolved_sections.get("key_insights") or [],
        "what_to_focus_on": resolved_sections.get("what_to_focus_on") or [],
        "evidence_quality": resolved_sections["evidence_quality"],
        "summary": resolved_sections["system_state"],
        "themes": [
            str(item.get("driver")).strip()
            for item in resolved_sections["top_drivers"]
            if isinstance(item, dict) and str(item.get("driver") or "").strip()
        ][:4],
        "weekly_behavior_metrics": weekly_behavior_metrics,
        "aggregated_journal_analysis": aggregated_journal_analysis,
        "unified_correlations": unified_correlations,
        # Backward-compatible alias.
        "behavior_correlations": behavior_correlations,
    }
    insight_text = format_weekly_behavioral_insight(structured_output)

    if existing:
        result = db.execute(
            text(
                """
                UPDATE ai_insights
                SET insight_date = CURRENT_DATE,
                    period_type = 'weekly',
                    model_provider = 'anthropic',
                    model_name = 'claude-haiku-4-5',
                    prompt_version = :prompt_version,
                    input_payload = CAST(:input_payload AS jsonb),
                    insight_text = :insight_text,
                    structured_output = CAST(:structured_output AS jsonb),
                    status = 'complete',
                    error_message = NULL,
                    updated_at = NOW()
                WHERE id = :insight_id
                RETURNING id, insight_type, period_start, period_end, insight_text, structured_output, created_at
                """
            ),
            {
                "insight_id": existing.id,
                "prompt_version": WEEKLY_BEHAVIORAL_PROMPT_VERSION,
                "input_payload": json.dumps(input_payload, default=str),
                "insight_text": insight_text,
                "structured_output": json.dumps(structured_output, default=str),
            },
        ).fetchone()
    else:
        result = db.execute(
            text(
                """
                INSERT INTO ai_insights (
                    insight_type,
                    insight_date,
                    period_start,
                    period_end,
                    period_type,
                    category,
                    model_provider,
                    model_name,
                    prompt_version,
                    input_payload,
                    insight_text,
                    structured_output,
                    status
                )
                VALUES (
                    'journal_weekly_summary',
                    CURRENT_DATE,
                    :period_start,
                    :period_end,
                    'weekly',
                    'journal',
                    'anthropic',
                    'claude-haiku-4-5',
                    :prompt_version,
                    CAST(:input_payload AS jsonb),
                    :insight_text,
                    CAST(:structured_output AS jsonb),
                    'complete'
                )
                RETURNING id, insight_type, period_start, period_end, insight_text, structured_output, created_at
                """
            ),
            {
                "period_start": period_start,
                "period_end": period_end,
                "prompt_version": WEEKLY_BEHAVIORAL_PROMPT_VERSION,
                "input_payload": json.dumps(input_payload, default=str),
                "insight_text": insight_text,
                "structured_output": json.dumps(structured_output, default=str),
            },
        ).fetchone()

    db.commit()

    return {
        "id": result.id,
        "insight_type": result.insight_type,
        "period_start": str(result.period_start),
        "period_end": str(result.period_end),
        "insight_text": result.insight_text,
        "structured_output": result.structured_output,
        "created_at": result.created_at,
        "entry_count": len(rows),
        "journal_ids": journal_ids,
        "average_mood_score": average_mood_score,
    }


@router.post("/journal/monthly-summary")
def create_monthly_journal_summary(
    payload: JournalWeeklyPeriodRequest | None = None,
    db: Session = Depends(get_db),
):
    period_start, period_end = _resolve_monthly_window(payload)
    rows = _load_weekly_analysis_rows(db, period_start, period_end)

    if not rows:
        latest_entry_date = _latest_analyzed_entry_date(db)
        if latest_entry_date is None:
            raise HTTPException(status_code=404, detail="No analyzed journal entries exist yet.")

        if payload and payload.period_start and payload.period_end:
            raise HTTPException(status_code=404, detail="No journal analyses found for the requested period.")

        period_start, period_end = _month_bounds(latest_entry_date)
        rows = _load_weekly_analysis_rows(db, period_start, period_end)
        if not rows:
            raise HTTPException(status_code=404, detail="No journal analyses found for any month.")

    analyses, journal_ids, average_mood_score = _serialize_weekly_analyses(rows)

    existing = db.execute(
        text("""
        SELECT id, insight_type, period_start, period_end, insight_text, structured_output, created_at
        FROM ai_insights
        WHERE category = 'journal'
          AND insight_type = 'journal_monthly_summary'
          AND period_start = :period_start
          AND period_end = :period_end
        ORDER BY created_at DESC
        LIMIT 1
        """),
        {"period_start": period_start, "period_end": period_end},
    ).fetchone()

    if existing:
        return {
            **dict(existing._mapping),
            "entry_count": len(rows),
            "journal_ids": journal_ids,
            "average_mood_score": average_mood_score,
        }

    structured = build_journal_period_summary(
        analyses=analyses,
        period_type="monthly",
        period_start=str(period_start),
        period_end=str(period_end),
    )

    input_payload = {
        "period_type": "monthly",
        "source_type": "journal_analyses",
        "entry_count": len(rows),
        "journal_ids": journal_ids,
        "average_mood_score": average_mood_score,
        "analyses": analyses,
    }

    result = db.execute(
        text("""
        INSERT INTO ai_insights (
            insight_type,
            insight_date,
            period_start,
            period_end,
            period_type,
            category,
            model_provider,
            model_name,
            prompt_version,
            input_payload,
            insight_text,
            structured_output,
            status
        )
        VALUES (
            'journal_monthly_summary',
            CURRENT_DATE,
            :period_start,
            :period_end,
            'monthly',
            'journal',
            'anthropic',
            'claude-haiku-4-5',
            'v3-monthly-from-journal-analyses',
            CAST(:input_payload AS jsonb),
            :insight_text,
            CAST(:structured_output AS jsonb),
            'complete'
        )
        RETURNING id, insight_type, period_start, period_end, insight_text, structured_output, created_at
        """),
        {
            "period_start": period_start,
            "period_end": period_end,
            "input_payload": json.dumps(input_payload, default=str),
            "insight_text": structured.get("summary", ""),
            "structured_output": json.dumps(structured, default=str),
        }
    ).fetchone()

    db.commit()

    return {
        "id": result.id,
        "insight_type": result.insight_type,
        "period_start": str(result.period_start),
        "period_end": str(result.period_end),
        "insight_text": result.insight_text,
        "structured_output": result.structured_output,
        "created_at": result.created_at,
        "entry_count": len(rows),
        "journal_ids": journal_ids,
        "average_mood_score": average_mood_score,
    }

@router.get("/journal/weekly-summary")
def get_weekly_journal_summaries(db: Session = Depends(get_db)):
    rows = db.execute(
        text("""
        SELECT id, insight_type, period_start, period_end, insight_text, structured_output, created_at
        FROM ai_insights
        WHERE category = 'journal'
          AND insight_type = 'journal_weekly_summary'
        ORDER BY period_start DESC, created_at DESC
        """)
    ).fetchall()

    return [dict(row._mapping) for row in rows]


@router.get("/journal/monthly-summary")
def get_monthly_journal_summaries(db: Session = Depends(get_db)):
    rows = db.execute(
        text("""
        SELECT id, insight_type, period_start, period_end, insight_text, structured_output, created_at
        FROM ai_insights
        WHERE category = 'journal'
          AND insight_type = 'journal_monthly_summary'
        ORDER BY period_start DESC, created_at DESC
        """)
    ).fetchall()

    return [dict(row._mapping) for row in rows]


@router.get("/journal/monthly-profile")
def get_monthly_journal_profiles(db: Session = Depends(get_db)):
    rows = (
        db.query(JournalPatternProfile)
        .filter(JournalPatternProfile.period_type == "monthly")
        .order_by(
            JournalPatternProfile.period_start.desc(),
            JournalPatternProfile.created_at.desc()
        )
        .all()
    )
    return rows


@router.get("/journal/profiles")
def get_journal_profiles(period_type: str | None = None, db: Session = Depends(get_db)):
    query = db.query(JournalPatternProfile)
    if period_type:
        query = query.filter(JournalPatternProfile.period_type == period_type)

    rows = query.order_by(
        JournalPatternProfile.period_start.desc(),
        JournalPatternProfile.created_at.desc()
    ).all()

    return rows

@router.get("/journal/profiles/latest", response_model=JournalPatternProfileOut)
def get_latest_journal_profile(db: Session = Depends(get_db)):
    row = (
        db.query(JournalPatternProfile)
        .order_by(JournalPatternProfile.created_at.desc())
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="No journal pattern profiles yet.")
    return row


@router.get("/latest")
def get_latest_insight(db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT id, insight_type, insight_date, period_start, period_end, category, insight_text, created_at
        FROM ai_insights
        ORDER BY created_at DESC
        LIMIT 1
    """)).fetchone()

    if not row:
        return {"message": "No insights yet"}

    return dict(row._mapping)


@router.get("/history")
def get_insight_history(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT id, insight_type, period_start, period_end, category, insight_text, created_at
        FROM ai_insights
        ORDER BY created_at DESC
        LIMIT 20
    """)).fetchall()

    return [dict(row._mapping) for row in rows]
