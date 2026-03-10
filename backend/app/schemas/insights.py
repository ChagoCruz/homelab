from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel


class InsightOut(BaseModel):
    id: int
    insight_type: str
    category: str
    insight_text: str
    insight_date: date
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    source_table: Optional[str] = None
    source_id: Optional[int] = None
    input_payload: Optional[dict[str, Any]] = None
    structured_output: Optional[dict[str, Any]] = None
    status: str
    created_at: datetime