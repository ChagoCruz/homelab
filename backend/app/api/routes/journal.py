from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import Journal, JournalEntryAnalysis
from app.schemas.journal import JournalCreate, JournalOut
from app.schemas.journal_ai import JournalEntryAnalysisOut
from app.services.claude_service import analyze_journal_entry_structured

router = APIRouter(prefix="/journal", tags=["Journal"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[JournalOut])
def read_journals(db: Session = Depends(get_db)):
    return db.query(Journal).order_by(Journal.entry_date.desc(), Journal.id.desc()).all()


@router.get("/{journal_id}/analysis", response_model=JournalEntryAnalysisOut)
def get_journal_analysis(journal_id: int, db: Session = Depends(get_db)):
    analysis = (
        db.query(JournalEntryAnalysis)
        .filter(JournalEntryAnalysis.journal_entry_id == journal_id)
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found for this journal entry.")
    return analysis


@router.post("/", response_model=JournalOut)
def create_journal(journal: JournalCreate, db: Session = Depends(get_db)):
    db_journal = Journal(**journal.model_dump())
    db.add(db_journal)
    db.commit()
    db.refresh(db_journal)

    try:
        structured = analyze_journal_entry_structured(
            {
                "entry_date": db_journal.entry_date,
                "content": db_journal.content,
            }
        )

        analysis = JournalEntryAnalysis(
            journal_entry_id=db_journal.id,
            model_provider="anthropic",
            model_name="claude-haiku-4-5",
            prompt_version="v2",
            mood_score=structured.get("mood_score"),
            emotional_tone=structured.get("emotional_tone"),
            key_emotions=structured.get("key_emotions", []),
            stressors=structured.get("stressors", []),
            positive_signals=structured.get("positive_signals", []),
            thinking_patterns=structured.get("thinking_patterns", []),
            life_direction_signals=structured.get("life_direction_signals", []),
            reflection_questions=structured.get("reflection_questions", []),
            insight=structured.get("insight"),
            encouragement=structured.get("encouragement"),
            raw_output=structured,
        )

        db.add(analysis)
        db.commit()

    except Exception:
        # Keep journal creation successful even if AI analysis fails.
        db.rollback()

    return db_journal