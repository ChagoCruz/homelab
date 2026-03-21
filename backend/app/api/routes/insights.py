from __future__ import annotations

from datetime import date, timedelta
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Journal, JournalEntryAnalysis, JournalPatternProfile
from app.schemas.journal_ai import JournalPatternProfileOut
from app.services.claude_service import (
    build_journal_pattern_profile,
    build_journal_period_summary,
)
from app.services.ollama_service import generate_weekly_report

router = APIRouter(prefix="/insights", tags=["insights"])

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


def _month_bounds(anchor_date: date) -> tuple[date, date]:
    period_start = anchor_date.replace(day=1)
    if period_start.month == 12:
        next_month_start = date(period_start.year + 1, 1, 1)
    else:
        next_month_start = date(period_start.year, period_start.month + 1, 1)
    period_end = next_month_start - timedelta(days=1)
    return period_start, period_end


def _coerce_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _coerce_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str):
            item = item.strip()
            if item:
                out.append(item)
    return out


def _load_weekly_profile_rows_for_month(db: Session, period_start: date, period_end: date) -> list[JournalPatternProfile]:
    rows = (
        db.query(JournalPatternProfile)
        .filter(
            JournalPatternProfile.period_type == "weekly",
            JournalPatternProfile.period_end >= period_start,
            JournalPatternProfile.period_start <= period_end,
        )
        .order_by(
            JournalPatternProfile.period_start.asc(),
            JournalPatternProfile.period_end.asc(),
            JournalPatternProfile.created_at.asc(),
        )
        .all()
    )

    # Weekly profiles are not unique by period range; keep only the newest row per range.
    latest_by_period: dict[tuple[date, date], JournalPatternProfile] = {}
    for row in rows:
        latest_by_period[(row.period_start, row.period_end)] = row

    return sorted(
        latest_by_period.values(),
        key=lambda row: (row.period_start, row.period_end, row.created_at),
    )


def _resolve_monthly_profile_window(db: Session) -> tuple[date, date, list[JournalPatternProfile]]:
    period_start, period_end = _month_bounds(date.today())
    weekly_profiles = _load_weekly_profile_rows_for_month(db, period_start, period_end)
    if weekly_profiles:
        return period_start, period_end, weekly_profiles

    latest_weekly_end = (
        db.query(JournalPatternProfile.period_end)
        .filter(JournalPatternProfile.period_type == "weekly")
        .order_by(JournalPatternProfile.period_end.desc(), JournalPatternProfile.created_at.desc())
        .limit(1)
        .scalar()
    )
    if latest_weekly_end is None:
        raise HTTPException(status_code=404, detail="No weekly journal profiles exist yet.")

    period_start, period_end = _month_bounds(latest_weekly_end)
    weekly_profiles = _load_weekly_profile_rows_for_month(db, period_start, period_end)
    if not weekly_profiles:
        raise HTTPException(
            status_code=404,
            detail="No weekly journal profiles found for any month.",
        )

    return period_start, period_end, weekly_profiles


def _load_weekly_summary_rows_for_month(db: Session, period_start: date, period_end: date):
    return db.execute(
        text("""
        SELECT id, period_start, period_end, insight_text, structured_output, created_at
        FROM ai_insights
        WHERE category = 'journal'
          AND insight_type = 'journal_weekly_summary'
          AND period_end >= :period_start
          AND period_start <= :period_end
        ORDER BY period_start ASC, period_end ASC, created_at ASC
        """),
        {"period_start": period_start, "period_end": period_end},
    ).fetchall()


def _resolve_monthly_summary_window(db: Session):
    period_start, period_end = _month_bounds(date.today())
    weekly_summaries = _load_weekly_summary_rows_for_month(db, period_start, period_end)
    if weekly_summaries:
        return period_start, period_end, weekly_summaries

    latest_weekly_end = db.execute(
        text("""
        SELECT period_end
        FROM ai_insights
        WHERE category = 'journal'
          AND insight_type = 'journal_weekly_summary'
        ORDER BY period_end DESC, created_at DESC
        LIMIT 1
        """)
    ).scalar()
    if latest_weekly_end is None:
        raise HTTPException(status_code=404, detail="No weekly journal summaries exist yet.")

    period_start, period_end = _month_bounds(latest_weekly_end)
    weekly_summaries = _load_weekly_summary_rows_for_month(db, period_start, period_end)
    if not weekly_summaries:
        raise HTTPException(
            status_code=404,
            detail="No weekly journal summaries found for any month.",
        )

    return period_start, period_end, weekly_summaries

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
        latest_entry_date = (
            db.query(Journal.entry_date)
            .join(JournalEntryAnalysis, JournalEntryAnalysis.journal_entry_id == Journal.id)
            .order_by(Journal.entry_date.desc(), Journal.id.desc())
            .limit(1)
            .scalar()
        )

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
def create_monthly_journal_profile(db: Session = Depends(get_db)):
    period_start, period_end, weekly_profiles = _resolve_monthly_profile_window(db)

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

    analyses = []
    mood_scores = []
    total_entries = 0

    for weekly in weekly_profiles:
        mood_value = float(weekly.average_mood_score) if weekly.average_mood_score is not None else None
        if mood_value is not None:
            mood_scores.append(mood_value)
        total_entries += int(weekly.entry_count or 0)

        analyses.append(
            {
                "journal_entry_id": f"weekly-profile-{weekly.id}",
                "entry_date": str(weekly.period_end),
                "mood_score": mood_value,
                "emotional_tone": "",
                "key_emotions": weekly.dominant_emotions or [],
                "stressors": weekly.recurring_stressors or [],
                "positive_signals": weekly.recurring_positive_signals or [],
                "thinking_patterns": weekly.recurring_thinking_patterns or [],
                "life_direction_signals": weekly.recurring_life_direction_signals or [],
                "insight": weekly.pattern_summary or "",
                "reflection_questions": [],
                "encouragement": "",
                "source_week_profile_id": int(weekly.id),
                "source_week_period_start": str(weekly.period_start),
                "source_week_period_end": str(weekly.period_end),
                "source_entry_count": int(weekly.entry_count or 0),
            }
        )

    structured = build_journal_pattern_profile(
        analyses=analyses,
        period_type="monthly",
        period_start=str(period_start),
        period_end=str(period_end),
    )

    average_mood_score = (
        round(sum(mood_scores) / len(mood_scores), 2) if mood_scores else structured.get("average_mood_score")
    )

    profile = JournalPatternProfile(
        period_type="monthly",
        period_start=period_start,
        period_end=period_end,
        entry_count=total_entries,
        model_provider="anthropic",
        model_name="claude-haiku-4-5",
        prompt_version="v3-monthly-from-weekly-profiles",
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
            "source_type": "weekly_profiles",
            "source_week_count": len(weekly_profiles),
            "source_total_entry_count": total_entries,
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
                'v3-monthly-from-weekly-profiles',
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
                    "source_type": "weekly_profiles",
                    "source_week_count": len(weekly_profiles),
                    "source_total_entry_count": total_entries,
                    "source_weekly_profiles": analyses,
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
        latest_entry_date = (
            db.query(Journal.entry_date)
            .join(JournalEntryAnalysis, JournalEntryAnalysis.journal_entry_id == Journal.id)
            .order_by(Journal.entry_date.desc(), Journal.id.desc())
            .limit(1)
            .scalar()
        )

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
        text("""
        SELECT id, insight_type, period_start, period_end, insight_text, structured_output, created_at
        FROM ai_insights
        WHERE category = 'journal'
          AND insight_type = 'journal_weekly_summary'
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
        period_type="weekly",
        period_start=str(period_start),
        period_end=str(period_end),
    )

    input_payload = {
        "period_type": "weekly",
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
            'journal',
            'anthropic',
            'claude-haiku-4-5',
            'v1',
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


@router.post("/journal/monthly-summary")
def create_monthly_journal_summary(db: Session = Depends(get_db)):
    period_start, period_end, weekly_summaries = _resolve_monthly_summary_window(db)

    source_weekly_summary_ids = [int(row.id) for row in weekly_summaries]

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
            "source_week_count": len(weekly_summaries),
            "source_weekly_summary_ids": source_weekly_summary_ids,
        }

    analyses = []
    themes_set = set()
    for row in weekly_summaries:
        structured_output = _coerce_json_object(row.structured_output)
        themes = _coerce_str_list(structured_output.get("themes"))
        for theme in themes:
            themes_set.add(theme)

        analyses.append(
            {
                "journal_entry_id": f"weekly-summary-{row.id}",
                "entry_date": str(row.period_end),
                "mood_score": None,
                "emotional_tone": "",
                "key_emotions": [],
                "stressors": _coerce_str_list(structured_output.get("stress_patterns")),
                "positive_signals": _coerce_str_list(structured_output.get("positive_patterns")),
                "thinking_patterns": _coerce_str_list(structured_output.get("emotional_trends")),
                "life_direction_signals": _coerce_str_list(structured_output.get("direction_signals")),
                "insight": structured_output.get("summary") or row.insight_text or "",
                "reflection_questions": _coerce_str_list(structured_output.get("reflection_questions")),
                "encouragement": "",
                "source_week_summary_id": int(row.id),
                "source_week_period_start": str(row.period_start),
                "source_week_period_end": str(row.period_end),
                "source_themes": themes,
            }
        )

    structured = build_journal_period_summary(
        analyses=analyses,
        period_type="monthly",
        period_start=str(period_start),
        period_end=str(period_end),
    )

    input_payload = {
        "period_type": "monthly",
        "source_type": "weekly_summaries",
        "source_week_count": len(weekly_summaries),
        "source_weekly_summary_ids": source_weekly_summary_ids,
        "source_themes": sorted(themes_set),
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
            'v2-monthly-from-weekly-summaries',
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
        "source_week_count": len(weekly_summaries),
        "source_weekly_summary_ids": source_weekly_summary_ids,
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
