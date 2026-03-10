import os
import json
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import Journal
from app.db.session import get_db
from app.services.claude_service import (
    generate_weekly_health_insight,
    generate_journal_entry_analysis,
    generate_journal_period_summary,
)

router = APIRouter(prefix="/insights", tags=["insights"])

MODEL_NAME = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")


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
                SELECT ROUND(AVG(total_calories)::numeric, 1)
                FROM daily_calories
            ),
            'alcohol_days', (
                SELECT COALESCE(SUM(had_alcohol), 0)
                FROM daily_calories
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
    insight_text = generate_weekly_health_insight(metrics)

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
            'anthropic',
            :model_name,
            'health-v1',
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
            "model_name": MODEL_NAME,
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


@router.post("/journal/weekly")
def analyze_journal_weekly(db: Session = Depends(get_db)):
    period_end = date.today()
    period_start = period_end - timedelta(days=6)

    entries = (
        db.query(Journal)
        .filter(Journal.entry_date >= period_start, Journal.entry_date <= period_end)
        .order_by(Journal.entry_date.asc(), Journal.id.asc())
        .all()
    )

    if not entries:
        raise HTTPException(status_code=404, detail="No journal entries found for this period")

    payload = [
        {
            "journal_id": row.id,
            "entry_date": row.entry_date,
            "content": row.content,
            "word_count": len((row.content or "").split()),
        }
        for row in entries
    ]

    insight_text = generate_journal_period_summary(payload)

    structured_output = {
        "entry_count": len(payload),
        "journal_ids": [x["journal_id"] for x in payload],
    }

    sql = text("""
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
            :model_name,
            'journal-v1',
            CAST(:input_payload AS jsonb),
            :insight_text,
            CAST(:structured_output AS jsonb),
            'complete'
        )
        RETURNING id, insight_type, category, insight_text, created_at
    """)

    result = db.execute(
        sql,
        {
            "period_start": period_start,
            "period_end": period_end,
            "model_name": MODEL_NAME,
            "input_payload": json.dumps(payload, default=str),
            "insight_text": insight_text,
            "structured_output": json.dumps(structured_output, default=str),
        },
    ).fetchone()

    db.commit()

    return {
        **dict(result._mapping),
        "period_start": str(period_start),
        "period_end": str(period_end),
        "entry_count": len(payload),
    }


@router.get("/journal/history")
def get_journal_insight_history(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT
            id,
            insight_type,
            insight_date,
            period_start,
            period_end,
            category,
            source_table,
            source_id,
            insight_text,
            created_at
        FROM ai_insights
        WHERE category = 'journal'
        ORDER BY created_at DESC
        LIMIT 20
    """)).fetchall()

    return [dict(row._mapping) for row in rows]


@router.post("/journal/{journal_id}")
def analyze_journal_entry(journal_id: int, db: Session = Depends(get_db)):
    journal = db.query(Journal).filter(Journal.id == journal_id).first()
    if not journal:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    payload = {
        "journal_id": journal.id,
        "entry_date": journal.entry_date,
        "content": journal.content,
        "word_count": len((journal.content or "").split()),
    }

    insight_text = generate_journal_entry_analysis(payload)

    structured_output = {
        "journal_id": journal.id,
        "word_count": payload["word_count"],
    }

    sql = text("""
        INSERT INTO ai_insights (
            insight_type,
            insight_date,
            category,
            source_table,
            source_id,
            model_provider,
            model_name,
            prompt_version,
            input_payload,
            insight_text,
            structured_output,
            status
        )
        VALUES (
            'journal_entry_analysis',
            CURRENT_DATE,
            'journal',
            'journal',
            :source_id,
            'anthropic',
            :model_name,
            'journal-v1',
            CAST(:input_payload AS jsonb),
            :insight_text,
            CAST(:structured_output AS jsonb),
            'complete'
        )
        RETURNING id, insight_type, category, insight_text, created_at
    """)

    result = db.execute(
        sql,
        {
            "source_id": journal.id,
            "model_name": MODEL_NAME,
            "input_payload": json.dumps(payload, default=str),
            "insight_text": insight_text,
            "structured_output": json.dumps(structured_output, default=str),
        },
    ).fetchone()

    db.commit()

    return dict(result._mapping)


@router.get("/journal/{journal_id}")
def get_journal_insights(journal_id: int, db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT
            id,
            insight_type,
            insight_date,
            category,
            source_table,
            source_id,
            insight_text,
            structured_output,
            created_at
        FROM ai_insights
        WHERE source_table = 'journal'
          AND source_id = :journal_id
        ORDER BY created_at DESC
    """), {"journal_id": journal_id}).fetchall()

    return [dict(row._mapping) for row in rows]


@router.get("/latest")
def get_latest_insight(db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT
            id,
            insight_type,
            insight_date,
            period_start,
            period_end,
            category,
            source_table,
            source_id,
            insight_text,
            created_at
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
        SELECT
            id,
            insight_type,
            period_start,
            period_end,
            category,
            source_table,
            source_id,
            insight_text,
            created_at
        FROM ai_insights
        ORDER BY created_at DESC
        LIMIT 20
    """)).fetchall()

    return [dict(row._mapping) for row in rows]