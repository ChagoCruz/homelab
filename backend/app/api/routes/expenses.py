from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.session import SessionLocal
from app.db.models import Expense
from app.schemas.expenses import ExpenseCreate, ExpenseOut

router = APIRouter(prefix="/expenses", tags=["Expense"])

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=list[ExpenseOut])
def read_expenses(db: Session = Depends(get_db)):
    return db.query(Expense).all()

@router.post("/", response_model=ExpenseOut)
def create_expense(expense: ExpenseCreate, db: Session = Depends(get_db)):
    db_expense = Expense(**expense.dict())
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense