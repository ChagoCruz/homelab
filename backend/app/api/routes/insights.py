from datetime import date, timedelta
import json

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
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
                    CASE
                        WHEN meal = 'drink' AND food ILIKE 'beer%' THEN 1
                        ELSE 0
                    END
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
            insight_text,
            created_at
        FROM ai_insights
        ORDER BY created_at DESC
        LIMIT 20
    """)).fetchall()

    return [dict(row._mapping) for row in rows]