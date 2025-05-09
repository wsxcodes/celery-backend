from typing import Optional

from pydantic import BaseModel


class Customer(BaseModel):
    customer_id: str
    output_language: Optional[str] = "Czech"
    file_count: int


class UpdateCustomer(BaseModel):
    output_language: Optional[str] = "Czech"
    file_count: Optional[int] = 0
