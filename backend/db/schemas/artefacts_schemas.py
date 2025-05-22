from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class AImode(str, Enum):
    standard = "standard"
    detailed = "detailed"


class AIAlert(str, Enum):
    alert = "alert"
    action_required = "action_required"
    insights_available = "insights_available"
    reminder = "reminder"
    none = None


class AnalysisStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    processed = "processed"


class Artefact(BaseModel):
    id: int
    customer_id: str
    uuid: str
    filename: str
    file_size: Optional[int] = None
    hash_sha256: Optional[str] = None
    uploaded_at: datetime
    analysis_status: AnalysisStatus = AnalysisStatus.pending
    analysis_started_at: Optional[datetime] = None
    analysis_completed_at: Optional[datetime] = None
    ai_output_language: Optional[str] = "English"
    ai_analysis_mode: Optional[AImode] = AImode.standard
    ai_alert_status: Optional[AIAlert] = AIAlert.none
    ai_expires: Optional[datetime] = None
    ai_is_expired: Optional[bool] = None
    ai_category: Optional[str] = ""
    ai_sub_category: Optional[str] = ""
    ai_summary_short: Optional[str] = ""
    ai_summary_long: Optional[str] = ""
    ai_analysis_criteria: Optional[str] = ""
    ai_features_and_insights: Optional[Any] = ""
    ai_alerts_and_actions: Optional[Any] = ""
    ai_eterny_legacy_schema: Optional[Any] = ""
    document_raw_text: Optional[str] = ""
    webhook_url: Optional[str] = ""


class ArtefactUpdate(BaseModel):
    analysis_status: AnalysisStatus = AnalysisStatus.pending
    analysis_started_at: Optional[datetime] = None
    analysis_completed_at: Optional[datetime] = None
    ai_output_language: Optional[str] = "English"
    ai_analysis_mode: Optional[AImode] = AImode.standard
    ai_alert_status: Optional[AIAlert] = AIAlert.none
    ai_expires: Optional[datetime] = None
    ai_is_expired: Optional[bool] = None
    ai_category: Optional[str] = ""
    ai_sub_category: Optional[str] = ""
    ai_summary_short: Optional[str] = ""
    ai_summary_long: Optional[str] = ""
    ai_analysis_criteria: Optional[str] = ""
    ai_features_and_insights: Optional[Any] = ""
    ai_alerts_and_actions: Optional[Any] = ""
    ai_eterny_legacy_schema: Optional[Any] = ""
    document_raw_text: Optional[str] = ""
    webhook_url: Optional[str] = ""
