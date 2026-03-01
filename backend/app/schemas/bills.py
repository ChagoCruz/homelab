from pydantic import BaseModel
from datetime import date
from typing import Optional, List

class BillCreate(BaseModel):
    name: str
    amount: float
    due_date: date
    paid: bool
    paid_date: Optional[date] = None
    
class BillOut(BillCreate):
    id: int 
    class Config:
        orm_mode = True