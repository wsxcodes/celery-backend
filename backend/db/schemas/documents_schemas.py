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
    file_preview: Optional[str] = ""
    uploaded_at: datetime
    analysis_status: AnalysisStatus = AnalysisStatus.pending
    analysis_started_at: Optional[datetime] = None
    analysis_completed_at: Optional[datetime] = None
    analysis_cost: int = 0
    ai_alert: Optional[AIAlert] = AIAlert.none
    ai_expires: Optional[datetime] = None
    ai_category: Optional[str] = ""
    ai_sub_category: Optional[str] = ""
    ai_summary_short: Optional[str] = ""
    ai_summary_long: Optional[str] = ""
    ai_enterny_legacy_schema: Optional[str] = ""
    raw_text: Optional[str] = ""
    health_score: Optional[int] = 0


class DocumentUpdate(BaseModel):
    file_preview: Optional[str] = ""
    analysis_status: AnalysisStatus = AnalysisStatus.pending
    analysis_started_at: Optional[datetime] = None
    analysis_completed_at: Optional[datetime] = None
    analysis_cost: int = 0
    ai_alert: Optional[AIAlert] = AIAlert.none
    ai_expires: Optional[datetime] = None
    ai_category: Optional[str] = ""
    ai_sub_category: Optional[str] = ""
    ai_summary_short: Optional[str] = ""
    ai_summary_long: Optional[str] = ""
    raw_text: Optional[str] = ""
    health_score: Optional[int] = 0
    ai_enterny_legacy_schema: Optional[str] = ""
