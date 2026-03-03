from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class HealthDaySummary(BaseModel):
  date: date
  weight: Optional[float] = None
  systolic: Optional[int] = None
  diastolic: Optional[int] = None
  calories_in: int = 0
  calories_out: int = 0
  calories_net: int = 0  # in - out


class BloodPressurePoint(BaseModel):
  date: date
  systolic: int
  diastolic: int


class HealthDashboardOut(BaseModel):
  end_date: date
  days: int
  series: List[HealthDaySummary] = []
  bp_last_7: List[BloodPressurePoint] = []