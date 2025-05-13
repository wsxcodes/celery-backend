from typing import Optional, Dict
from pydantic import BaseModel, model_validator


class MessagePayload(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None

    @model_validator(mode='after')
    def check_one_present(cls, model):
        if not (model.question or model.answer):
            raise ValueError("Either question or answer must be provided")
        return model
