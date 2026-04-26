import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class EventCreate(BaseModel):
    workspace_id: uuid.UUID
    session_id: uuid.UUID | None = None
    message_id: uuid.UUID | None = None
    event_type: Literal['code_copy', 'completion']
    event_metadata: dict = {}


class EventResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    session_id: uuid.UUID | None
    message_id: uuid.UUID | None
    event_type: str
    event_metadata: dict
    created_at: datetime

    model_config = {'from_attributes': True}
