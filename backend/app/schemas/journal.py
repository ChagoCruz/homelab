from pydantic import BaseModel
from datetime import date

class JournalCreate(BaseModel):
    entry_date: date
    content: str

class JournalOut(JournalCreate):
    id: int

    class Config:
        from_attributes = True  # SQLAlchemy 2.0 replacement for orm_mode