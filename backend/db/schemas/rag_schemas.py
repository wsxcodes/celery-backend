from typing import Optional, Dict
from pydantic import BaseModel, model_validator
from datetime import datetime
from typing import Literal


class MessagePayload(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None

    @model_validator(mode='after')
    def check_one_present(cls, model):
        if not (model.question or model.answer):
            raise ValueError("Either question or answer must be provided")
        return model


class RAGMessage(BaseModel):
    id: int
    document_uuid: str
    message_type: Literal['question', 'answer']
    content: str
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }
