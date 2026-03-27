import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, JSON, Integer, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Agent(Base):
    __tablename__ = 'agents'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    owner_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Model configuration
    model: Mapped[str] = mapped_column(String(100), default='gpt-4o-mini')
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)

    # Evolution tracking
    generation: Mapped[int] = mapped_column(Integer, default=1)
    fitness_score: Mapped[float] = mapped_column(Float, default=0.0)
    total_interactions: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    interactions: Mapped[list['Interaction']] = relationship(
        'Interaction', back_populates='agent', cascade='all, delete-orphan'
    )


class Interaction(Base):
    __tablename__ = 'interactions'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('agents.id'), nullable=False, index=True
    )

    input: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[str] = mapped_column(Text, nullable=False)
    feedback_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    agent: Mapped['Agent'] = relationship('Agent', back_populates='interactions')
