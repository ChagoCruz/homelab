from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.schemas.tarot import TarotCardDraw

router = APIRouter(prefix="/tarot", tags=["Tarot"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/spread", response_model=list[TarotCardDraw])
def get_tarot_spread(db: Session = Depends(get_db)):
    query = text(
        """
        WITH deck AS (
            SELECT
                id,
                name,
                full_summary,
                row_number() OVER (ORDER BY random()) AS pos
            FROM tarot_cards
            LIMIT 3
        ),
        orientations AS (
            SELECT
                s.pos,
                s.r,
                CASE WHEN s.r < 0.5 THEN 'upright' ELSE 'reversed' END AS orientation
            FROM (
                SELECT generate_series(1, 3) AS pos, random() AS r
            ) AS s
        )
        SELECT
            CASE d.pos
                WHEN 1 THEN 'Past'
                WHEN 2 THEN 'Present'
                WHEN 3 THEN 'Future'
            END AS position,
            d.name,
            o.orientation,
            d.full_summary
        FROM deck d
        JOIN orientations o USING (pos)
        ORDER BY d.pos;
        """
    )

    rows = db.execute(query).mappings().all()
    return [
        {
            "position": row["position"],
            "name": row["name"],
            "orientation": row["orientation"],
            "full_summary": row["full_summary"],
        }
        for row in rows
    ]