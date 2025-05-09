from pydantic import BaseModel
from datetime import datetime

class FileRecord(BaseModel):
    id: int
    customer_id: str
    filename: str
    uploaded_at: datetime
