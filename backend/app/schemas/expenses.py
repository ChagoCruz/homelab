from pydantic import BaseModel
from datetime import date

class ExpenseCreate(BaseModel):
    amount: float
    description: str
    spent_date: date
    category: str
        
class ExpenseOut(ExpenseCreate):
    id: int
    class Config:
        orm_mode = True