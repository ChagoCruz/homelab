from sqlalchemy import Column, Integer, String, Date
from app.db.base import Base

class Journal(Base):
    __tablename__ = "journal"

    id = Column(Integer, primary_key=True, index=True)
    entry_date = Column(Date)
    content = Column(String)

class TarotCard(Base):
    __tablename__ = "tarot_cards"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    full_summary = Column(String)