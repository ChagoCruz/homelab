from typing import List, Optional
from pydantic import BaseModel

from app.schemas.weight import WeightOut, WeightUpdate
from app.schemas.blood_pressure import BloodPressureOut, BloodPressureUpdate
from app.schemas.diet import DietOut, DietUpsert
from app.schemas.workout import WorkoutOut, WorkoutUpsert


class HealthDayOut(BaseModel):
  weight: Optional[WeightOut] = None
  blood_pressure: Optional[BloodPressureOut] = None
  diet: List[DietOut] = []
  workouts: List[WorkoutOut] = []


class HealthDayUpsert(BaseModel):
  weight: Optional[WeightUpdate] = None
  blood_pressure: Optional[BloodPressureUpdate] = None
  diet: List[DietUpsert] = []
  workouts: List[WorkoutUpsert] = []