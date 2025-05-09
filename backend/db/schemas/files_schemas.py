from datetime import datetime

from pydantic import BaseModel


class FileRecord(BaseModel):
    id: int
    customer_id: str
    filename: str
    uploaded_at: datetime
