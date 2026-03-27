import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    model: str = Field('gpt-4o-mini', max_length=100)
    system_prompt: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class AgentResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    model: str
    system_prompt: Optional[str]
    config: Dict[str, Any]
    generation: int
    fitness_score: float
    total_interactions: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {'from_attributes': True}


class InteractionCreate(BaseModel):
    input: str = Field(..., min_length=1)
    meta: Dict[str, Any] = Field(default_factory=dict)


class FeedbackPayload(BaseModel):
    interaction_id: uuid.UUID
    score: float = Field(..., ge=0.0, le=5.0)


class InteractionResponse(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    input: str
    output: str
    feedback_score: Optional[float]
    tokens_used: Optional[int]
    latency_ms: Optional[int]
    meta: Dict[str, Any]
    created_at: datetime

    model_config = {'from_attributes': True}
