from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field


class Session(BaseModel):
    id: str
    label: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    question_count: int = 0
