from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.stats import (
    DailyLifeFactOut,
    WeeklyHistoryOut,
    WeeklyKpiDeltaOut,
    WeeklyLifeSummaryDashboardOut,
    WeeklyLifeSummaryOut,
)

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


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _build_weekly_kpi(current: object, previous: object) -> WeeklyKpiDeltaOut:
    current_value = _to_float(current)
    previous_value = _to_float(previous)
    delta_value = None
    if current_value is not None and previous_value is not None:
        delta_value = current_value - previous_value

    return WeeklyKpiDeltaOut(
        current=current_value,
        previous_week_value=previous_value,
        delta_from_previous_week=delta_value,
    )


@router.get("/weekly-life-summary", response_model=list[WeeklyLifeSummaryOut] | WeeklyLifeSummaryDashboardOut)
def get_weekly_life_summary(
    start_date: date | None = None,
    end_date: date | None = None,
    week_start: date | None = None,
    view: Literal["list", "dashboard"] = Query(default="list"),
    history_weeks: int = Query(default=8, ge=6, le=8),
    db: Session = Depends(get_db),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be on or before end_date")

    if view == "list":
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

    selected_week_start_query = text(
        """
        SELECT COALESCE(:week_start_filter, MAX(week_start)) AS selected_week_start
        FROM vw_weekly_life_summary
        WHERE (:start_date IS NULL OR week_start >= :start_date)
          AND (:end_date IS NULL OR week_start <= :end_date)
        """
    )
    selected_week_start = db.execute(
        selected_week_start_query,
        {
            "week_start_filter": week_start,
            "start_date": start_date,
            "end_date": end_date,
        },
    ).scalar_one_or_none()

    weekly_kpi_row: dict[str, object] | None = None
    if selected_week_start is not None:
        weekly_kpi_query = text(
            """
            SELECT
                cur.week_start,
                cur.week_end,
                cur.food_total_calories AS current_total_food_calories,
                prev.food_total_calories AS previous_total_food_calories,
                cur.drink_total_calories AS current_total_drink_calories,
                prev.drink_total_calories AS previous_total_drink_calories,
                cur.alc_total_calories AS current_total_beer_calories,
                prev.alc_total_calories AS previous_total_beer_calories,
                cur.total_workout_calories AS current_total_exercise_calories,
                prev.total_workout_calories AS previous_total_exercise_calories,
                cur.net_calories AS current_net_calories,
                prev.net_calories AS previous_net_calories,
                cur.avg_daily_calories AS current_avg_daily_calories_in,
                prev.avg_daily_calories AS previous_avg_daily_calories_in,
                cur.avg_daily_workout_calories AS current_avg_daily_calories_out,
                prev.avg_daily_workout_calories AS previous_avg_daily_calories_out
            FROM vw_weekly_life_summary cur
            LEFT JOIN LATERAL (
                SELECT
                    p.food_total_calories,
                    p.drink_total_calories,
                    p.alc_total_calories,
                    p.total_workout_calories,
                    p.net_calories,
                    p.avg_daily_calories,
                    p.avg_daily_workout_calories
                FROM vw_weekly_life_summary p
                WHERE p.week_start < cur.week_start
                ORDER BY p.week_start DESC
                LIMIT 1
            ) AS prev ON TRUE
            WHERE cur.week_start = :selected_week_start
            LIMIT 1
            """
        )
        weekly_kpi_row = db.execute(
            weekly_kpi_query,
            {"selected_week_start": selected_week_start},
        ).mappings().first()

    safety_query = text(
        """
        SELECT
            (CURRENT_DATE - MAX(entry_date))::int AS days_since_last_safety_meeting
        FROM safety_meeting_daily
        """
    )
    days_since_last_safety_meeting = db.execute(safety_query).scalar_one_or_none()

    weekly_history_rows: list[dict[str, object]] = []
    if selected_week_start is not None:
        weekly_history_query = text(
            """
            SELECT
                week_start,
                week_end,
                food_total_calories AS total_food_calories,
                drink_total_calories AS total_drink_calories,
                alc_total_calories AS total_beer_calories,
                total_workout_calories AS total_exercise_calories,
                net_calories,
                avg_daily_calories AS avg_daily_calories_in,
                avg_daily_workout_calories AS avg_daily_calories_out
            FROM vw_weekly_life_summary
            WHERE week_start <= :selected_week_start
              AND (:start_date IS NULL OR week_start >= :start_date)
              AND (:end_date IS NULL OR week_start <= :end_date)
            ORDER BY week_start DESC
            LIMIT :history_weeks
            """
        )
        weekly_history_rows = db.execute(
            weekly_history_query,
            {
                "selected_week_start": selected_week_start,
                "history_weeks": history_weeks,
                "start_date": start_date,
                "end_date": end_date,
            },
        ).mappings().all()

    return WeeklyLifeSummaryDashboardOut(
        week_start=weekly_kpi_row.get("week_start") if weekly_kpi_row else selected_week_start,
        week_end=weekly_kpi_row.get("week_end") if weekly_kpi_row else None,
        total_food_calories=_build_weekly_kpi(
            weekly_kpi_row.get("current_total_food_calories") if weekly_kpi_row else None,
            weekly_kpi_row.get("previous_total_food_calories") if weekly_kpi_row else None,
        ),
        total_drink_calories=_build_weekly_kpi(
            weekly_kpi_row.get("current_total_drink_calories") if weekly_kpi_row else None,
            weekly_kpi_row.get("previous_total_drink_calories") if weekly_kpi_row else None,
        ),
        total_beer_calories=_build_weekly_kpi(
            weekly_kpi_row.get("current_total_beer_calories") if weekly_kpi_row else None,
            weekly_kpi_row.get("previous_total_beer_calories") if weekly_kpi_row else None,
        ),
        total_exercise_calories=_build_weekly_kpi(
            weekly_kpi_row.get("current_total_exercise_calories") if weekly_kpi_row else None,
            weekly_kpi_row.get("previous_total_exercise_calories") if weekly_kpi_row else None,
        ),
        net_calories=_build_weekly_kpi(
            weekly_kpi_row.get("current_net_calories") if weekly_kpi_row else None,
            weekly_kpi_row.get("previous_net_calories") if weekly_kpi_row else None,
        ),
        avg_daily_calories_in=_build_weekly_kpi(
            weekly_kpi_row.get("current_avg_daily_calories_in") if weekly_kpi_row else None,
            weekly_kpi_row.get("previous_avg_daily_calories_in") if weekly_kpi_row else None,
        ),
        avg_daily_calories_out=_build_weekly_kpi(
            weekly_kpi_row.get("current_avg_daily_calories_out") if weekly_kpi_row else None,
            weekly_kpi_row.get("previous_avg_daily_calories_out") if weekly_kpi_row else None,
        ),
        days_since_last_safety_meeting=days_since_last_safety_meeting,
        weekly_history=[WeeklyHistoryOut.model_validate(dict(row)) for row in weekly_history_rows],
    )
