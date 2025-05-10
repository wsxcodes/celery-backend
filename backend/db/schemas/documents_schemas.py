from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class AIAlert(str, Enum):
    none = None
    insights_available = "insights_available"
    action_required = "action_required"
    reminder = "reminder"
    alert = "alert"


class AnalysisStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    processed = "processed"


class Document(BaseModel):
    id: int
    customer_id: str
    uuid: str
    filename: str
    file_size: Optional[int] = None
    file_hash: str
    uploaded_at: datetime
    analysis_status: AnalysisStatus = AnalysisStatus.pending
    analysis_started_at: Optional[datetime] = None
    analysis_completed_at: Optional[datetime] = None
    analysis_cost: int = 0
    ai_alert: Optional[AIAlert] = AIAlert.none
    ai_category: Optional[str] = ""
    ai_summary_short: Optional[str] = ""
    ai_summary_long: Optional[str] = ""


class DocumentUpdate(BaseModel):
    analysis_status: Optional[AnalysisStatus] = None
    analysis_started_at: Optional[datetime] = None
    analysis_completed_at: Optional[datetime] = None
    analysis_cost: Optional[int] = None
    ai_alert: Optional[AIAlert] = None
    ai_category: Optional[str] = None
    ai_summary_short: Optional[str] = None
    ai_summary_long: Optional[str] = None
