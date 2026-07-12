import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, JSON, Integer, Float, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

_DEFAULT_SYSTEM_PROMPT = """You are evoagent AI — an intelligent coding partner built on the evoagent.io platform. The routing, memory, and evolution logic running you was built by the Decision3 team — a unique, experimental system that we're actively developing and upgrading 24/7 with the latest available technology. Under the hood, we dynamically route between multiple models (currently including DeepSeek, Gemini, and Claude) for the best balance of cost and quality — but the platform, workflow, and continuous evolution around those models is what makes EvoAgent EvoAgent. If asked which specific model answered a given message, you can share that too — we build in the open."""


class Workspace(Base):
    __tablename__ = 'workspaces'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tech_stack: Mapped[list] = mapped_column(JSON, default=list)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    evo_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    evo_points_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    agent_profile: Mapped['AgentProfile'] = relationship(
        'AgentProfile',
        back_populates='workspace',
        uselist=False,
        cascade='all, delete-orphan',
    )
    sessions: Mapped[list['Session']] = relationship(
        'Session',
        back_populates='workspace',
        cascade='all, delete-orphan',
        order_by='Session.updated_at.desc()',
    )


class AgentProfile(Base):
    """
    One-to-one with Workspace. Holds the configuration for the coding partner
    in that workspace — model, system prompt, tuning parameters.
    """

    __tablename__ = 'agent_profiles'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('workspaces.id'), nullable=False, unique=True
    )

    name: Mapped[str] = mapped_column(String(255), default='Coding Partner')
    model: Mapped[str] = mapped_column(String(100), default='deepseek/deepseek-chat')
    system_prompt: Mapped[str] = mapped_column(
        Text, default=_DEFAULT_SYSTEM_PROMPT, nullable=False
    )
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096)

    # Champion/Challenger A/B testing fields
    challenger_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    challenger_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active_variant: Mapped[str] = mapped_column(String(50), default='champion')

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    workspace: Mapped['Workspace'] = relationship(
        'Workspace', back_populates='agent_profile'
    )


class Session(Base):
    """
    A conversation thread within a Workspace. Users can have many sessions
    per workspace (e.g. one per feature, bug, or day of work).
    """

    __tablename__ = 'sessions'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('workspaces.id'), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), default='New session')
    status: Mapped[str] = mapped_column(String(50), default='active')

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    workspace: Mapped['Workspace'] = relationship('Workspace', back_populates='sessions')
    messages: Mapped[list['Message']] = relationship(
        'Message',
        back_populates='session',
        cascade='all, delete-orphan',
        order_by='Message.created_at.asc()',
    )


class Message(Base):
    __tablename__ = 'messages'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('sessions.id'), nullable=False, index=True
    )

    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Structured outputs: code blocks, step plans, file references
    artifacts: Mapped[list] = mapped_column(JSON, default=list)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fitness_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    session: Mapped['Session'] = relationship('Session', back_populates='messages')


class Feedback(Base):
    __tablename__ = 'feedback'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('messages.id'), nullable=False, index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('sessions.id'), nullable=False, index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('workspaces.id'), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
