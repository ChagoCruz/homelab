from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class JournalEntryAnalysisOut(BaseModel):
    id: int
    journal_entry_id: int
    model_provider: str
    model_name: str
    prompt_version: str
    mood_score: Decimal | None = None
    emotional_tone: str | None = None
    key_emotions: list[str] = Field(default_factory=list)
    stressors: list[str] = Field(default_factory=list)
    positive_signals: list[str] = Field(default_factory=list)
    thinking_patterns: list[str] = Field(default_factory=list)
    life_direction_signals: list[str] = Field(default_factory=list)
    reflection_questions: list[str] = Field(default_factory=list)
    insight: str | None = None
    encouragement: str | None = None
    raw_output: dict[str, Any] | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class JournalPatternProfileOut(BaseModel):
    id: int
    period_type: str
    period_start: date
    period_end: date
    entry_count: int
    model_provider: str
    model_name: str
    prompt_version: str
    average_mood_score: Decimal | None = None
    dominant_emotions: list[str] = Field(default_factory=list)
    recurring_stressors: list[str] = Field(default_factory=list)
    recurring_positive_signals: list[str] = Field(default_factory=list)
    recurring_thinking_patterns: list[str] = Field(default_factory=list)
    recurring_life_direction_signals: list[str] = Field(default_factory=list)
    core_values: list[str] = Field(default_factory=list)
    motivation_drivers: list[str] = Field(default_factory=list)
    growth_signals: list[str] = Field(default_factory=list)
    risk_signals: list[str] = Field(default_factory=list)
    pattern_summary: str | None = None
    raw_output: dict[str, Any] | None = None
    created_at: datetime

    class Config:
        from_attributes = True