from pydantic import BaseModel
from datetime import date, datetime

class JournalCreate(BaseModel):
    entry_date: date
    content: str

class JournalOut(JournalCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True  # SQLAlchemy 2.0 replacement for orm_mode