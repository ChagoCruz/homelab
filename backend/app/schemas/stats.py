from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class DailyLifeFactOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    day: date

    journal_count: int
    avg_mood_score: float | None = None
    min_mood_score: float | None = None
    max_mood_score: float | None = None
    had_journal: bool
    had_journal_analysis: bool

    total_entry_count: int
    total_calories: float
    food_entry_count: int
    food_calories: float
    drink_entry_count: int
    drink_calories: float
    alcohol_entry_count: int
    alcohol_calories: float
    had_alcohol: bool

    avg_weight: float | None = None
    avg_systolic: float | None = None
    avg_diastolic: float | None = None
    workout_entry_count: int
    total_workout_calories: float
    had_weight: bool
    had_blood_pressure: bool
    had_workout: bool

    weather_code: int | None = None
    weather_summary: str | None = None
    temp_max_f: float | None = None
    temp_min_f: float | None = None
    sunrise: datetime | None = None
    sunset: datetime | None = None
    moon_phase_percent: float | None = None
    moon_phase_name: str | None = None
    had_rain: bool
    had_snow: bool
    had_clouds: bool
    had_sun: bool

    safety_meeting: bool
    temp_band: str | None = None


class WeeklyLifeSummaryOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    week_start: date
    week_end: date

    days_in_week: int

    journal_count: int
    days_with_journal: int
    days_with_journal_analysis: int
    avg_mood_score: float | None = None
    min_mood_score: float | None = None
    max_mood_score: float | None = None

    total_entry_count: int
    total_calories: float
    avg_daily_calories: float | None = None
    food_entry_count: int
    food_total_calories: float
    food_avg_daily_calories: float | None = None
    drink_entry_count: int
    drink_total_calories: float
    drink_avg_daily_calories: float | None = None
    alc_entry_count: int
    alc_total_calories: float
    alc_avg_daily_calories: float | None = None
    alcohol_days: int

    avg_weight: float | None = None
    min_weight: float | None = None
    max_weight: float | None = None
    avg_systolic: float | None = None
    avg_diastolic: float | None = None
    workout_entry_count: int
    total_workout_calories: float
    avg_daily_workout_calories: float | None = None
    workout_days: int

    net_calories: float

    avg_temp_max_f: float | None = None
    avg_temp_min_f: float | None = None
    hottest_temp_f: float | None = None
    coldest_temp_f: float | None = None
    rain_days: int
    snow_days: int
    cloudy_days: int
    sunny_days: int
    weather_summaries: list[str] = Field(default_factory=list)
    temp_bands: list[str] = Field(default_factory=list)

    safety_meeting_days: int

    key_emotions: list[str] = Field(default_factory=list)
    stressors: list[str] = Field(default_factory=list)
    positive_signals: list[str] = Field(default_factory=list)
    thinking_patterns: list[str] = Field(default_factory=list)
    life_direction_signals: list[str] = Field(default_factory=list)
