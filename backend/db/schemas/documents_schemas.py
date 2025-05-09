from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Document(BaseModel):
    id: int
    customer_id: str
    uuid: str
    filename: str
    file_size: Optional[int] = None
    file_hash: str
    uploaded_at: datetime
    analysis_status: str = "pending"
    analysis_started_at: Optional[datetime] = None
    analysis_completed_at: Optional[datetime] = None
    analysis_cost: int = 0
    ai_summary_short: Optional[str] = None
    ai_summary_long: Optional[str] = None


class DocumentUpdate(BaseModel):
    analysis_status: Optional[str] = None
    analysis_started_at: Optional[datetime] = None
    analysis_completed_at: Optional[datetime] = None
    analysis_cost: Optional[int] = None
    ai_summary_short: Optional[str] = None
    ai_summary_long: Optional[str] = None
