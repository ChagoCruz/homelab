from datetime import date
from typing import Optional
from pydantic import BaseModel


class WorkoutBase(BaseModel):
  workout_date: date
  workout: Optional[str] = None
  calories_burnt: Optional[int] = None


class WorkoutCreate(WorkoutBase):
  pass


class WorkoutUpsert(BaseModel):
  id: Optional[int] = None
  workout_date: date
  workout: Optional[str] = None
  calories_burnt: Optional[int] = None


class WorkoutOut(WorkoutBase):
  id: int

  class Config:
    from_attributes = True