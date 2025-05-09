from datetime import datetime

from pydantic import BaseModel


class Customer(BaseModel):
    customer_id: str
    file_count: int
    
class FileRecord(BaseModel):
    id: int
    uuid: str
    customer_id: str
    filename: str
    file_hash: str
    uploaded_at: datetime
