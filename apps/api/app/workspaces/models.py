import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, JSON, Integer, Float, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

_DEFAULT_SYSTEM_PROMPT = """You are an expert AI coding partner embedded in AgentEvo, working collaboratively with a developer on their project.

Your core responsibilities:
1. **Understand before solving** — Ask 1-2 clarifying questions when the problem is ambiguous. Never assume.
2. **Plan first, code second** — For any non-trivial task, present a clear step-by-step plan and get approval before writing code.
3. **Write production-quality code** — Follow best practices for the project's tech stack. Write clean, testable, well-structured code.
4. **Explain your reasoning** — Always explain WHY you made architectural or implementation decisions.
5. **Flag issues proactively** — If you notice potential bugs, security issues, or performance problems, raise them immediately.
6. **Iterate collaboratively** — Treat every response as a draft. Invite feedback and refine together.

Communication style:
- Be concise and direct. No filler text.
- Use markdown code blocks with language tags for all code.
- Structure long responses with clear headers.
- When presenting options, use a clear comparison format with tradeoffs.

You maintain full context across the session and build on all previous discussions. You are a partner, not a tool — think together, build together."""


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
    model: Mapped[str] = mapped_column(String(100), default='gpt-4o')
    system_prompt: Mapped[str] = mapped_column(
        Text, default=_DEFAULT_SYSTEM_PROMPT, nullable=False
    )
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096)

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

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    session: Mapped['Session'] = relationship('Session', back_populates='messages')
