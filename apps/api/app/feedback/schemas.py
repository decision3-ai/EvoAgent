import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, model_validator


class FeedbackCreate(BaseModel):
    session_id: uuid.UUID | None = None
    agent_name: str | None = None
    task_type: str | None = None
    model_used: str
    system_prompt: str | None = None
    user_input: str
    agent_output: str
    feedback_type: Literal['up', 'down', 'correction']
    corrected_output: str | None = None
    confidence_score: float | None = None
    rating: int | None = None
    extra_metadata: dict | None = None

    @model_validator(mode='after')
    def correction_requires_output(self) -> 'FeedbackCreate':
        if self.feedback_type == 'correction' and not self.corrected_output:
            raise ValueError('corrected_output is required when feedback_type is correction')
        return self


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime
    session_id: uuid.UUID | None
    user_id: str | None
    agent_name: str | None
    task_type: str | None
    model_used: str
    system_prompt: str | None
    user_input: str
    agent_output: str
    feedback_type: str
    corrected_output: str | None
    confidence_score: float | None
    rating: int | None
    extra_metadata: dict | None

    model_config = {'from_attributes': True}
