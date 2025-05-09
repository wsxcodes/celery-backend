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
    ai_alert: Optional[str] = ""
    ai_category: Optional[str] = ""
    ai_summary_short: Optional[str] = ""
    ai_summary_long: Optional[str] = ""


class DocumentUpdate(BaseModel):
    analysis_status: Optional[str] = None
    analysis_started_at: Optional[datetime] = None
    analysis_completed_at: Optional[datetime] = None
    analysis_cost: Optional[int] = None
    ai_alert: Optional[str] = None
    ai_category: Optional[str] = None
    ai_summary_short: Optional[str] = None
    ai_summary_long: Optional[str] = None
