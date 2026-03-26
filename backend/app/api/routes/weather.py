from __future__ import annotations

from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import WeatherDaily
from app.db.session import get_db
from app.schemas.weather import WeatherDailyOut, WeatherIngestResponse
from app.services.weather_service import fetch_daily_weather

router = APIRouter(prefix="/weather", tags=["weather"])


@router.post("/ingest", response_model=WeatherIngestResponse)
def ingest_weather(db: Session = Depends(get_db)):
    try:
        payload = fetch_daily_weather()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch weather data: {exc}")

    weather_date = datetime.fromisoformat(payload["weather_date"]).date()
    sunrise = datetime.fromisoformat(payload["sunrise"])
    sunset = datetime.fromisoformat(payload["sunset"])

    existing = db.query(WeatherDaily).filter(WeatherDaily.weather_date == weather_date).first()
    if existing:
        return WeatherIngestResponse(
            status="already_exists",
            created=False,
            weather_date=existing.weather_date,
            weather_summary=existing.weather_summary,
        )

    row = WeatherDaily(
        weather_date=weather_date,
        weather_code=payload["weather_code"],
        weather_summary=payload["weather_summary"],
        temp_max_f=payload["temp_max_f"],
        temp_min_f=payload["temp_min_f"],
        sunrise=sunrise,
        sunset=sunset,
        moon_phase_percent=payload["moon_phase_percent"],
        moon_phase_name=payload["moon_phase_name"],
        raw_payload=payload["raw_payload"],
    )

    db.add(row)
    db.commit()
    db.refresh(row)

    return WeatherIngestResponse(
        status="inserted",
        created=True,
        weather_date=row.weather_date,
        weather_summary=row.weather_summary,
    )

@router.get("/latest", response_model=WeatherDailyOut)
def get_latest_weather(db: Session = Depends(get_db)):
    row = (
        db.query(WeatherDaily)
        .order_by(WeatherDaily.weather_date.desc())
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="No weather rows found.")

    return row

@router.get("/{weather_date}", response_model=WeatherDailyOut)
def get_weather_by_date(weather_date: date, db: Session = Depends(get_db)):
    row = (
        db.query(WeatherDaily)
        .filter(WeatherDaily.weather_date == weather_date)
        .first()
    )

    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"No weather row found for {weather_date}."
        )

    return row