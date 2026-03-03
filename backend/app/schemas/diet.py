from datetime import date
from typing import Optional
from pydantic import BaseModel


class DietBase(BaseModel):
  log_date: date
  meal: Optional[str] = None
  food: Optional[str] = None
  calories: Optional[int] = None
  confidence: Optional[str] = None


class DietCreate(DietBase):
  pass


class DietUpsert(BaseModel):
  id: Optional[int] = None
  log_date: date
  meal: Optional[str] = None
  food: Optional[str] = None
  calories: Optional[int] = None
  confidence: Optional[str] = None


class DietOut(DietBase):
  id: int

  class Config:
    from_attributes = True