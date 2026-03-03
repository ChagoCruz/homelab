from datetime import date
from typing import Optional
from pydantic import BaseModel


class BloodPressureBase(BaseModel):
  entry_date: date
  systolic: Optional[int] = None
  diastolic: Optional[int] = None  # mapped from DB column "diatolic"


class BloodPressureCreate(BloodPressureBase):
  pass


class BloodPressureUpdate(BaseModel):
  id: Optional[int] = None
  entry_date: date
  systolic: Optional[int] = None
  diastolic: Optional[int] = None


class BloodPressureOut(BloodPressureBase):
  id: int

  class Config:
    from_attributes = True