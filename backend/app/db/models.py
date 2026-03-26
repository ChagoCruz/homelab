from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Float,
    Boolean,
    BigInteger,
    Text,
    DateTime,
    ForeignKey,
    TIMESTAMP,
    Numeric,
)
from sqlalchemy.sql import func
from app.db.base import Base
from sqlalchemy.dialects.postgresql import JSONB


class Bill(Base):
  __tablename__ = "bills"

  id = Column(Integer, primary_key=True, index=True)
  name = Column(String)
  amount = Column(Float)
  due_date = Column(Date)
  paid = Column(Boolean)
  paid_date = Column(Date, nullable=True)


class CarMileage(Base):
  __tablename__ = "car_mileage"

  id = Column(Integer, primary_key=True, index=True)
  log_date = Column(Date)
  odometer = Column(Integer)


class Expense(Base):
  __tablename__ = "expenses"

  id = Column(Integer, primary_key=True, index=True)
  amount = Column(Float)
  description = Column(String)
  spent_date = Column(Date)
  category = Column(String)


class Income(Base):
  __tablename__ = "income"

  id = Column(Integer, primary_key=True, index=True)
  source = Column(String)
  amount = Column(Float)
  received_date = Column(Date)
  notes = Column(String)


class Journal(Base):
  __tablename__ = "journal"

  id = Column(Integer, primary_key=True, index=True)
  entry_date = Column(Date)
  content = Column(Text)
  created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TarotCard(Base):
  __tablename__ = "tarot_cards"

  id = Column(Integer, primary_key=True, index=True)
  name = Column(String)
  full_summary = Column(String)


# -----------------------------
# Health tables (already exist in your DB)
# -----------------------------

class Weight(Base):
  __tablename__ = "weight"

  id = Column(Integer, primary_key=True, index=True)
  entry_date = Column(Date)
  weight = Column(Float)


class BloodPressure(Base):
  __tablename__ = "blood_pressure"

  id = Column(Integer, primary_key=True, index=True)
  entry_date = Column(Date)
  systolic = Column(Integer)
  diastolic = Column(Integer)


class Diet(Base):
  __tablename__ = "diet"

  id = Column(Integer, primary_key=True, index=True)
  log_date = Column(Date)
  meal = Column(String)
  food = Column(String)
  calories = Column(Integer)
  confidence = Column(String)


class Workout(Base):
  __tablename__ = "workout"

  id = Column(Integer, primary_key=True, index=True)
  workout_date = Column(Date)
  workout = Column(String)
  calories_burnt = Column(Integer)

class JournalEntryAnalysis(Base):
  __tablename__ = "journal_entry_analysis"

  id = Column(BigInteger, primary_key=True, index=True)
  journal_entry_id = Column(BigInteger, ForeignKey("journal.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

  model_provider = Column(String, nullable=False, default="anthropic")
  model_name = Column(String, nullable=False, default="claude-haiku-4-5")
  prompt_version = Column(String, nullable=False, default="v2")

  mood_score = Column(Numeric(4, 2), nullable=True)
  emotional_tone = Column(String, nullable=True)

  key_emotions = Column(JSONB, nullable=False, default=list)
  stressors = Column(JSONB, nullable=False, default=list)
  positive_signals = Column(JSONB, nullable=False, default=list)
  thinking_patterns = Column(JSONB, nullable=False, default=list)
  life_direction_signals = Column(JSONB, nullable=False, default=list)
  reflection_questions = Column(JSONB, nullable=False, default=list)

  insight = Column(Text, nullable=True)
  encouragement = Column(Text, nullable=True)
  raw_output = Column(JSONB, nullable=True)

  created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class JournalPatternProfile(Base):
  __tablename__ = "journal_pattern_profile"

  id = Column(BigInteger, primary_key=True, index=True)

  period_type = Column(String, nullable=False)  # weekly, monthly, yearly, rolling_10_entries
  period_start = Column(Date, nullable=False, index=True)
  period_end = Column(Date, nullable=False, index=True)
  entry_count = Column(Integer, nullable=False, default=0)

  model_provider = Column(String, nullable=False, default="anthropic")
  model_name = Column(String, nullable=False, default="claude-haiku-4-5")
  prompt_version = Column(String, nullable=False, default="v2")

  average_mood_score = Column(Numeric(4, 2), nullable=True)

  dominant_emotions = Column(JSONB, nullable=False, default=list)
  recurring_stressors = Column(JSONB, nullable=False, default=list)
  recurring_positive_signals = Column(JSONB, nullable=False, default=list)
  recurring_thinking_patterns = Column(JSONB, nullable=False, default=list)
  recurring_life_direction_signals = Column(JSONB, nullable=False, default=list)
  core_values = Column(JSONB, nullable=False, default=list)
  motivation_drivers = Column(JSONB, nullable=False, default=list)
  growth_signals = Column(JSONB, nullable=False, default=list)
  risk_signals = Column(JSONB, nullable=False, default=list)

  pattern_summary = Column(Text, nullable=True)
  raw_output = Column(JSONB, nullable=True)

  created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

class WeatherDaily(Base):
    __tablename__ = "weather_daily"

    id = Column(BigInteger, primary_key=True, index=True)
    weather_date = Column(Date, nullable=False, unique=True, index=True)

    weather_code = Column(Integer, nullable=True)
    weather_summary = Column(Text, nullable=False)

    temp_max_f = Column(Numeric(5, 2), nullable=True)
    temp_min_f = Column(Numeric(5, 2), nullable=True)

    sunrise = Column(TIMESTAMP, nullable=True)
    sunset = Column(TIMESTAMP, nullable=True)

    moon_phase_percent = Column(Numeric(5, 2), nullable=True)
    moon_phase_name = Column(Text, nullable=True)

    raw_payload = Column(JSONB, nullable=True)

    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())