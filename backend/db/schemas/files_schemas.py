from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class Customer(BaseModel):
    customer_id: str
    file_count: int


class FileRecord(BaseModel):
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
