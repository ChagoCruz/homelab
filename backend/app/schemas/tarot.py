from pydantic import BaseModel
from datetime import date

class TarotCardDraw(BaseModel):
    position: str
    name: str
    orientation: str
    full_summary: str