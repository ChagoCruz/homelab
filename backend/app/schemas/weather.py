from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class WeatherDailyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    weather_date: date
    weather_code: Optional[int] = None
    weather_summary: str
    temp_max_f: Optional[float] = None
    temp_min_f: Optional[float] = None
    sunrise: Optional[datetime] = None
    sunset: Optional[datetime] = None
    moon_phase_percent: Optional[float] = None
    moon_phase_name: Optional[str] = None
    raw_payload: Optional[Any] = None
    created_at: datetime


class WeatherIngestResponse(BaseModel):
    status: str
    created: bool
    weather_date: date
    weather_summary: str