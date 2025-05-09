from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Customer(BaseModel):
    customer_id: str
    file_count: int


class Document(BaseModel):
    id: int
    customer_id: str
    uuid: str
    filename: str
    file_hash: str
    uploaded_at: datetime
    analysis_status: str = "pending"
    analysis_started_at: Optional[datetime] = None
    analysis_completed_at: Optional[datetime] = None
    analysis_cost: int = 0
    file_size: Optional[int] = None


class DocumentUpdate(BaseModel):
    analysis_status: Optional[str] = None
    analysis_started_at: Optional[datetime] = None
    analysis_completed_at: Optional[datetime] = None
    analysis_cost: Optional[int] = None
