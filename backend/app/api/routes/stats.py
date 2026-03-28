from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.stats import DailyLifeFactOut, WeeklyLifeSummaryOut

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/daily-life-facts", response_model=list[DailyLifeFactOut])
def get_daily_life_facts(
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int | None = Query(default=None, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be on or before end_date")

    params: dict[str, object] = {
        "start_date": start_date,
        "end_date": end_date,
    }

    if limit is None:
        query = text(
            """
            SELECT *
            FROM vw_daily_life_facts
            WHERE (:start_date IS NULL OR day >= :start_date)
              AND (:end_date IS NULL OR day <= :end_date)
            ORDER BY day ASC
            """
        )
    else:
        params["limit"] = limit
        query = text(
            """
            SELECT *
            FROM (
                SELECT *
                FROM vw_daily_life_facts
                WHERE (:start_date IS NULL OR day >= :start_date)
                  AND (:end_date IS NULL OR day <= :end_date)
                ORDER BY day DESC
                LIMIT :limit
            ) AS recent_days
            ORDER BY day ASC
            """
        )

    rows = db.execute(query, params).mappings().all()
    return [DailyLifeFactOut.model_validate(dict(row)) for row in rows]


@router.get("/weekly-life-summary", response_model=list[WeeklyLifeSummaryOut])
def get_weekly_life_summary(
    start_date: date | None = None,
    end_date: date | None = None,
    week_start: date | None = None,
    db: Session = Depends(get_db),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be on or before end_date")

    query = text(
        """
        SELECT *
        FROM vw_weekly_life_summary
        WHERE (:start_date IS NULL OR week_start >= :start_date)
          AND (:end_date IS NULL OR week_start <= :end_date)
          AND (:week_start_filter IS NULL OR week_start = :week_start_filter)
        ORDER BY week_start ASC
        """
    )

    rows = db.execute(
        query,
        {
            "start_date": start_date,
            "end_date": end_date,
            "week_start_filter": week_start,
        },
    ).mappings().all()

    return [WeeklyLifeSummaryOut.model_validate(dict(row)) for row in rows]
