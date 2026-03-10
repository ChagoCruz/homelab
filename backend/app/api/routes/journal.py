from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import Journal
from app.schemas.journal import JournalCreate, JournalOut

router = APIRouter(prefix="/journal", tags=["Journal"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[JournalOut])
def read_journals(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Journal)

    if start_date:
        query = query.filter(Journal.entry_date >= start_date)
    if end_date:
        query = query.filter(Journal.entry_date <= end_date)

    return query.order_by(Journal.entry_date.desc(), Journal.id.desc()).all()


@router.get("/{journal_id}", response_model=JournalOut)
def read_journal(journal_id: int, db: Session = Depends(get_db)):
    row = db.query(Journal).filter(Journal.id == journal_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return row


@router.post("/", response_model=JournalOut)
def create_journal(journal: JournalCreate, db: Session = Depends(get_db)):
    db_journal = Journal(**journal.model_dump())
    db.add(db_journal)
    db.commit()
    db.refresh(db_journal)
    return db_journal