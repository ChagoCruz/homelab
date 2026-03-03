from sqlalchemy import Column, Integer, String, Date, Float, Boolean
from app.db.base import Base


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
  content = Column(String)


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