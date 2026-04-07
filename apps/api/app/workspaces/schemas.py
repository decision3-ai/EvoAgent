import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List, Any


# ─── Agent Profile ────────────────────────────────────────────────────────────

class AgentProfileResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    model: str
    system_prompt: str
    temperature: float
    max_tokens: int
    created_at: datetime
    updated_at: datetime

    model_config = {'from_attributes': True}


class AgentProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=256, le=32768)


# ─── Workspace ────────────────────────────────────────────────────────────────

class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    tech_stack: List[str] = Field(default_factory=list)


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    tech_stack: Optional[List[str]] = None


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    tech_stack: List[str]
    is_default: bool
    created_at: datetime
    updated_at: datetime
    agent_profile: Optional[AgentProfileResponse] = None

    model_config = {'from_attributes': True}


# ─── Session ──────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    title: str = Field(default='New session', max_length=500)


class SessionUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = None


class SessionResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {'from_attributes': True}


# ─── Message / Chat ───────────────────────────────────────────────────────────

class Artifact(BaseModel):
    type: str  # "code" | "plan" | "file"
    language: Optional[str] = None
    filename: Optional[str] = None
    content: str


class MessageResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    artifacts: List[Any]
    tokens_used: Optional[int]
    latency_ms: Optional[int]
    fitness_score: Optional[float] = None
    created_at: datetime

    model_config = {'from_attributes': True}


class FeedbackCreate(BaseModel):
    score: int = Field(..., ge=1, le=5)


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    message_id: uuid.UUID
    session_id: uuid.UUID
    workspace_id: uuid.UUID
    score: int
    created_at: datetime

    model_config = {'from_attributes': True}


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
    session_title: str
