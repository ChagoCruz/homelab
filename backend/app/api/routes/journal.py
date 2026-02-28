from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.session import SessionLocal
from app.db.models import Journal
from app.schemas.journal import JournalCreate, JournalOut

router = APIRouter(prefix="/journal", tags=["Journal"])

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[JournalOut])
def read_journals(db: Session = Depends(get_db)):
    return db.query(Journal).all()


@router.post("/", response_model=JournalOut)
def create_journal(journal: JournalCreate, db: Session = Depends(get_db)):
    db_journal = Journal(**journal.model_dump())
    db.add(db_journal)
    db.commit()
    db.refresh(db_journal)
    return db_journal