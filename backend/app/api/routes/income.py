from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.session import SessionLocal
from app.db.models import Income 
from app.schemas.income import IncomeCreate, IncomeOut

router = APIRouter(prefix="/income", tags=["Income"])

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=list[IncomeOut])
def read_income(db: Session = Depends(get_db)):
    return db.query(Income).all()

@router.post("/", response_model=IncomeOut)
def create_income(income: IncomeCreate, db: Session = Depends(get_db)):
    db_income = Income(**income.dict())
    db.add(db_income)
    db.commit()
    db.refresh(db_income)
    return db_income