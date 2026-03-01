from pydantic import BaseModel
from datetime import date
from typing import Optional, List

class IncomeCreate(BaseModel):
    source: str 
    amount: float 
    received_date: date 
    notes: str

class IncomeOut(IncomeCreate):
    id: int 
    class Config:
        orm_mode = True 