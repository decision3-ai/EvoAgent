import os
import uuid
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, JSON, Integer, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from tasks import app

load_dotenv()

logger = logging.getLogger(__name__)

_DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+asyncpg://agentevo:agentevo_secret@postgres:5432/agentevo_db',
).replace('postgresql+asyncpg://', 'postgresql+psycopg2://')


class _Base(DeclarativeBase):
    pass


class _Agent(_Base):
    __tablename__ = 'agents'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    fitness_score: Mapped[float] = mapped_column(Float, default=0.0)
    interactions: Mapped[list['_Interaction']] = relationship(
        '_Interaction', back_populates='agent'
    )


class _Interaction(_Base):
    __tablename__ = 'interactions'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('agents.id'), nullable=False
    )
    feedback_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    agent: Mapped['_Agent'] = relationship('_Agent', back_populates='interactions')


def _make_engine():
    return create_engine(_DATABASE_URL, pool_pre_ping=True)


@app.task(name='tasks.agent_tasks.evolve_agent', bind=True, max_retries=3)
def evolve_agent(self, agent_id: str) -> dict:
    """
    Analyze an agent's recent interactions and trigger a prompt evolution.
    Dispatched automatically after every N interactions or via scheduled beat.

    Evolution pipeline (to be implemented with LangGraph):
    1. Load agent + last N interactions from DB
    2. Compute weak points from low-scored interactions
    3. Generate improved system prompt via LLM
    4. Store new generation; bump agent.generation counter
    5. Archive old prompt for rollback capability
    """
    try:
        logger.info('[EvolveTask] Starting evolution for agent %s', agent_id)

        # TODO: implement LangGraph evolution pipeline
        # from app.evolution.pipeline import run_evolution_pipeline
        # result = run_evolution_pipeline(agent_id)

        logger.info('[EvolveTask] Evolution complete for agent %s', agent_id)
        return {'status': 'evolved', 'agent_id': agent_id}

    except Exception as exc:
        logger.error('[EvolveTask] Failed for agent %s: %s', agent_id, exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@app.task(name='tasks.agent_tasks.compute_fitness', bind=True, max_retries=3)
def compute_fitness(self, agent_id: str) -> dict:
    """
    Compute fitness score for an agent from its interaction history.

    Aggregates all Interaction.feedback_score values (1–5 scale;
    thumbs up = 5, thumbs down = 1, null = ignored) and stores the
    average as agent.fitness_score.
    """
    logger.info('[FitnessTask] Computing fitness for agent %s', agent_id)
    try:
        engine = _make_engine()
        with Session(engine) as session:
            agent_uuid = uuid.UUID(agent_id)

            agent = session.get(_Agent, agent_uuid)
            if agent is None:
                logger.warning('[FitnessTask] Agent %s not found', agent_id)
                return {'agent_id': agent_id, 'fitness': None, 'status': 'not_found'}

            scores = session.execute(
                select(_Interaction.feedback_score)
                .where(_Interaction.agent_id == agent_uuid)
                .where(_Interaction.feedback_score.is_not(None))
            ).scalars().all()

            if not scores:
                logger.info('[FitnessTask] No feedback scores for agent %s', agent_id)
                return {'agent_id': agent_id, 'fitness': 0.0, 'status': 'no_data'}

            fitness = round(sum(scores) / len(scores), 4)

            agent.fitness_score = fitness
            session.commit()

        logger.info(
            '[FitnessTask] Agent %s fitness=%.4f (n=%d)', agent_id, fitness, len(scores)
        )
        return {'agent_id': agent_id, 'fitness': fitness, 'status': 'ok', 'n': len(scores)}

    except Exception as exc:
        logger.error('[FitnessTask] Failed for agent %s: %s', agent_id, exc, exc_info=True)
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


@app.task(name='tasks.agent_tasks.prune_old_interactions')
def prune_old_interactions(agent_id: str, keep_last: int = 500) -> dict:
    """
    Prune interaction history, keeping only the most recent N interactions
    to control storage growth on long-running agents.
    """
    logger.info(
        '[PruneTask] Pruning interactions for agent %s (keep_last=%d)',
        agent_id,
        keep_last,
    )
    # TODO: delete oldest interactions beyond keep_last threshold
    return {'agent_id': agent_id, 'kept': keep_last}
