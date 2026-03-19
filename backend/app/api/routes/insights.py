from __future__ import annotations

from datetime import date, timedelta
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Journal, JournalEntryAnalysis, JournalPatternProfile
from app.schemas.journal_ai import JournalPatternProfileOut
from app.services.claude_service import build_journal_pattern_profile
from app.services.ollama_service import generate_weekly_report

router = APIRouter(prefix="/insights", tags=["insights"])


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


@router.post("/journal/weekly", response_model=JournalPatternProfileOut)
def create_weekly_journal_profile(db: Session = Depends(get_db)):
    period_end = date.today()
    period_start = period_end - timedelta(days=6)

    def load_rows(window_start: date, window_end: date):
        return (
            db.query(JournalEntryAnalysis)
            .join(Journal, JournalEntryAnalysis.journal_entry_id == Journal.id)
            .filter(Journal.entry_date >= window_start, Journal.entry_date <= window_end)
            .all()
        )

    rows = load_rows(period_start, period_end)

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
        rows = load_rows(period_start, period_end)

    if not rows:
        raise HTTPException(status_code=404, detail="No journal analyses found for any 7-day period.")

    analyses = []
    mood_scores = []

    for row in rows:
        analyses.append(
            {
                "journal_entry_id": row.journal_entry_id,
                "mood_score": float(row.mood_score) if row.mood_score is not None else None,
                "emotional_tone": row.emotional_tone,
                "key_emotions": row.key_emotions or [],
                "stressors": row.stressors or [],
                "positive_signals": row.positive_signals or [],
                "thinking_patterns": row.thinking_patterns or [],
                "life_direction_signals": row.life_direction_signals or [],
                "insight": row.insight,
                "reflection_questions": row.reflection_questions or [],
                "encouragement": row.encouragement,
            }
        )
        if row.mood_score is not None:
            mood_scores.append(float(row.mood_score))

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

@router.get("/journal/profiles")
def get_journal_profiles(db: Session = Depends(get_db)):
    rows = (
        db.query(JournalPatternProfile)
        .order_by(
            JournalPatternProfile.period_start.desc(),
            JournalPatternProfile.created_at.desc()
        )
        .all()
    )

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
