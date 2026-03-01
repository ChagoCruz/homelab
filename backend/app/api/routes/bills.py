from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.session import SessionLocal
from app.db.models import Bill
from app.schemas.bills import BillCreate, BillOut

router = APIRouter(prefix="/bill", tags=["Bill"])

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=list[BillOut])
def read_bills(db: Session = Depends(get_db)):
    return db.query(Bill).all()

@router.post("/", response_model=BillOut)
def create_bill(bill: BillCreate, db: Session = Depends(get_db)):
    db_bill = Bill(**bill.dict())
    db.add(db_bill)
    db.commit()
    db.refresh(db_bill)
    return db_bill