from datetime import date
from typing import Optional
from pydantic import BaseModel


class WeightBase(BaseModel):
  entry_date: date
  weight: Optional[float] = None


class WeightCreate(WeightBase):
  pass


class WeightUpdate(BaseModel):
  id: Optional[int] = None
  entry_date: date
  weight: Optional[float] = None


class WeightOut(WeightBase):
  id: int

  class Config:
    from_attributes = True