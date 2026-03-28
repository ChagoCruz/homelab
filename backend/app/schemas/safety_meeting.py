from datetime import date
from pydantic import BaseModel


class SafetyMeetingDailyUpsert(BaseModel):
  completed: bool


class SafetyMeetingDailyOut(BaseModel):
  entry_date: date
  completed: bool
