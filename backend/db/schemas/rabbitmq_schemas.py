from typing import Any

from pydantic import BaseModel  # pylint: disable=no-name-in-module


class Msg(BaseModel):
    """MSG schema."""
    id: str
    result: Any = ""
    state: str = ""
