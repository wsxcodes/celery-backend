from enum import Enum
from typing import Optional

from pydantic import BaseModel


class AImode(str, Enum):
    standard = "standard"
    pedantic = "pedantic"


class Customer(BaseModel):
    id: int
    customer_id: str
    output_language: str = "Czech"
    ai_mode: AImode = AImode.standard
    file_count: int


class UpdateCustomer(BaseModel):
    output_language: Optional[str] = "Czech"
    ai_mode: Optional[AImode] = AImode.standard
    file_count: Optional[int] = 0
