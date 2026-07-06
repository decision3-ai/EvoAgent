import hashlib
import json
import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Optional, TypedDict
from urllib.parse import urlparse

import openai
import redis as redis_sync
from celery import chain
from dotenv import load_dotenv
from sqlalchemy import create_engine, func, select, text, String, Text, DateTime, Float
from sqlalchemy.orm import Session, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from tasks import app

load_dotenv()

logger = logging.getLogger(__name__)

_DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+asyncpg://agentevo:agentevo_secret@postgres:5432/agentevo_db',
).replace('postgresql+asyncpg://', 'postgresql+psycopg2://')

_EVOLUTION_MODEL = os.getenv('EVOLUTION_MODEL', 'anthropic/claude-haiku-4.5')
_OPENROUTER_BASE = 'https://openrouter.ai/api/v1'
_OLLAMA_BASE = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')


def _evolution_llm(temperature: float, max_tokens: int) -> ChatOpenAI:
    """Evolution/extraction LLM — Claude via OpenRouter (OpenAI-compatible)."""
    return ChatOpenAI(
        model=_EVOLUTION_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
        base_url=_OPENROUTER_BASE,
        api_key=os.getenv('OPENROUTER_API_KEY', ''),
    )

# Per-process flag — avoids re-running idempotent DDL on every task call
_schema_ready = False


# ---------------------------------------------------------------------------
# ORM models (sync / psycopg2)
# ---------------------------------------------------------------------------

class _Base(DeclarativeBase):
    pass


class _AgentProfile(_Base):
    """Workspace's agent profile — bridges agent_id to workspace_id for feedback lookup."""
    __tablename__ = 'agent_profiles'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    challenger_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    challenger_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active_variant: Mapped[str] = mapped_column(String(50), nullable=False, default='champion')
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_evolution_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    interactions_since_evolution: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class _Session(_Base):
    __tablename__ = 'sessions'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class _Message(_Base):
    __tablename__ = 'messages'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class _Feedback(_Base):
    __tablename__ = 'feedback'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class _AnalyticsEvent(_Base):
    """V2.1 event tracking — code_copy and completion events per workspace."""
    __tablename__ = 'analytics_events'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class _EvolutionHistory(_Base):
    """Daily fitness snapshots used for the consecutive-low-score trigger."""
    __tablename__ = 'evolution_history'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    fitness_score: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    baseline_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evolved_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


class _AgentMemory(_Base):
    """Typed session memories extracted per agent profile."""
    __tablename__ = 'agent_memories'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    # NOTE: workspace_id column is a FK to agent_profiles.id (named workspace_id in migration)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    importance_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    embedding = mapped_column(Vector(768), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ---------------------------------------------------------------------------
# Engine + schema helpers
# ---------------------------------------------------------------------------

def _make_engine():
    return create_engine(_DATABASE_URL, pool_pre_ping=True)


def _get_redis() -> redis_sync.Redis:
    return redis_sync.Redis.from_url(
        os.getenv('REDIS_URL', 'redis://redis:6379/0'),
        decode_responses=True,
    )


_mem0_client_sync = None


def _parse_mem0_db_url() -> dict:
    """Convert the worker's psycopg2 DATABASE_URL to plain params for mem0."""
    clean = _DATABASE_URL.replace('postgresql+psycopg2://', 'postgresql://')
    p = urlparse(clean)
    return {
        'host': p.hostname,
        'port': p.port or 5432,
        'dbname': p.path.lstrip('/'),
        'user': p.username,
        'password': p.password,
    }


def _get_mem0_client_sync():
    """Lazy singleton mem0 Memory client for use in sync Celery tasks."""
    global _mem0_client_sync
    if _mem0_client_sync is None:
        from mem0 import Memory  # lazy import — not always needed
        config = {
            'llm': {
                'provider': 'openai',  # OpenRouter is OpenAI-compatible
                'config': {
                    'model': _EVOLUTION_MODEL,
                    'api_key': os.getenv('OPENROUTER_API_KEY', ''),
                    'openai_base_url': _OPENROUTER_BASE,
                },
            },
            'embedder': {
                'provider': 'openai',  # Ollama is OpenAI-compatible
                'config': {
                    'api_key': 'ollama',
                    'model': 'nomic-embed-text',
                    'openai_base_url': f'{_OLLAMA_BASE}/v1',
                },
            },
            'vector_store': {
                'provider': 'pgvector',
                'config': {
                    **_parse_mem0_db_url(),
                    'collection_name': 'agent_memories',
                    'embedding_model_dims': 768,
                },
            },
        }
        _mem0_client_sync = Memory.from_config(config)
    return _mem0_client_sync


def _mem0_save_sync(workspace_id: str, messages: list, agent_id: str) -> None:
    """Synchronously add messages to mem0 vector store (worker-safe, no asyncio)."""
    client = _get_mem0_client_sync()
    client.add(messages, user_id=f'{workspace_id}:{agent_id}')


# Embedding client — Ollama via its OpenAI-compatible /v1 endpoint (sync)
_embed_client_sync: Optional[openai.OpenAI] = None


def _get_embed_client_sync() -> openai.OpenAI:
    """Lazy singleton for sync Ollama embedding client (OpenAI-compatible API)."""
    global _embed_client_sync
    if _embed_client_sync is None:
        _embed_client_sync = openai.OpenAI(
            base_url=f'{_OLLAMA_BASE}/v1',
            api_key='ollama',  # required by client, ignored by Ollama
        )
    return _embed_client_sync


def _embed_text_sync(text: str) -> Optional[List[float]]:
    """
    Generate embedding vector for text using Ollama nomic-embed-text (sync).
    Returns 768-dimensional vector or None on error.
    """
    try:
        client = _get_embed_client_sync()
        response = client.embeddings.create(
            model='nomic-embed-text',
            input=text,
        )
        return response.data[0].embedding
    except Exception:
        logger.exception('Ollama embedding failed')
        return None


def _ensure_schema(engine) -> None:
    """
    Idempotent DDL: adds new columns to agent_profiles and creates the
    evolution_history table if they don't exist yet.
    Called at most once per worker process (guarded by _schema_ready flag).
    No Alembic — raw ALTER TABLE / CREATE TABLE IF NOT EXISTS.
    """
    global _schema_ready
    if _schema_ready:
        return
    with engine.connect() as conn:
        conn.execute(text(
            'ALTER TABLE agent_profiles '
            'ADD COLUMN IF NOT EXISTS last_evolution_at TIMESTAMP;'
        ))
        conn.execute(text(
            'ALTER TABLE agent_profiles '
            'ADD COLUMN IF NOT EXISTS interactions_since_evolution INTEGER NOT NULL DEFAULT 0;'
        ))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS evolution_history (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                agent_profile_id UUID NOT NULL
                    REFERENCES agent_profiles(id) ON DELETE CASCADE,
                fitness_score FLOAT NOT NULL,
                recorded_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """))
        conn.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_evohist_agent_recorded '
            'ON evolution_history(agent_profile_id, recorded_at DESC);'
        ))
        conn.execute(text(
            'ALTER TABLE evolution_history '
            'ADD COLUMN IF NOT EXISTS notes TEXT;'
        ))
        conn.execute(text(
            'ALTER TABLE evolution_history '
            'ADD COLUMN IF NOT EXISTS baseline_hash VARCHAR(64);'
        ))
        conn.execute(text(
            'ALTER TABLE evolution_history '
            'ADD COLUMN IF NOT EXISTS evolved_hash VARCHAR(64);'
        ))
        conn.commit()
    _schema_ready = True
    logger.info('[Schema] Evolution schema ensured.')


# ---------------------------------------------------------------------------
# LangGraph evolution pipeline
# ---------------------------------------------------------------------------

class _EvolutionState(TypedDict):
    current_prompt: str
    feedback_items: list[str]
    weaknesses: str
    improved_prompt: str


def _analyze_weaknesses(state: _EvolutionState) -> dict:
    """Node 1: identify patterns in low-rated responses."""
    llm = _evolution_llm(temperature=0, max_tokens=1024)

    feedback_text = '\n'.join(f'- {item}' for item in state['feedback_items'])

    prompt = (
        'You are analyzing an AI coding assistant\'s performance.\n\n'
        f'Current system prompt:\n{state["current_prompt"]}\n\n'
        'The following are AI responses that received low user ratings (thumbs down):\n'
        f'{feedback_text}\n\n'
        'Identify 3–5 specific weaknesses or failure patterns in these responses. '
        'Be concrete and actionable — focus on what the agent did wrong, not what the user wanted.'
    )

    result = llm.invoke([HumanMessage(content=prompt)])
    return {'weaknesses': result.content}


def _generate_improved_prompt(state: _EvolutionState) -> dict:
    """Node 2: rewrite system_prompt to address identified weaknesses."""
    llm = _evolution_llm(temperature=0.3, max_tokens=2048)

    prompt = (
        'You are an expert at writing system prompts for AI coding assistants.\n\n'
        f'Current system prompt:\n{state["current_prompt"]}\n\n'
        f'Identified weaknesses to address:\n{state["weaknesses"]}\n\n'
        'Write an improved system prompt that:\n'
        '1. Preserves everything working well in the current prompt\n'
        '2. Specifically addresses each identified weakness\n'
        '3. Keeps the same structure, tone, and agent identity (evoagent AI)\n'
        '4. Does NOT reveal the underlying model or technology provider\n\n'
        'Return ONLY the new system prompt text — no commentary, no preamble.'
    )

    result = llm.invoke([HumanMessage(content=prompt)])
    return {'improved_prompt': result.content.strip()}


def _build_evolution_graph():
    graph = StateGraph(_EvolutionState)
    graph.add_node('analyze_weaknesses', _analyze_weaknesses)
    graph.add_node('generate_prompt', _generate_improved_prompt)
    graph.add_edge(START, 'analyze_weaknesses')
    graph.add_edge('analyze_weaknesses', 'generate_prompt')
    graph.add_edge('generate_prompt', END)
    return graph.compile()


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@app.task(name='tasks.agent_tasks.evolve_agent', bind=True, max_retries=3)
def evolve_agent(self, agent_id: str) -> dict:
    """
    Analyze an agent's recent low-rated interactions and evolve its system prompt.

    Steps:
    1. Load AgentProfile from DB by agent_id
    2. Fetch last 20 feedback records with score <= 2 for that workspace
    3. Use LangGraph to analyze weak points and generate an improved system_prompt
    4. Save the new system_prompt back to AgentProfile
    """
    try:
        logger.info('[EvolveTask] Starting evolution for agent %s', agent_id)

        engine = _make_engine()
        _ensure_schema(engine)
        with Session(engine) as session:
            agent_uuid = uuid.UUID(agent_id)

            profile = session.get(_AgentProfile, agent_uuid)
            if profile is None:
                logger.warning('[EvolveTask] No AgentProfile for agent %s', agent_id)
                return {'status': 'no_profile', 'agent_id': agent_id}

            # Fetch last 20 low-rated feedback records joined with message content
            rows = session.execute(
                select(_Message.content, _Message.role)
                .join(_Feedback, _Feedback.message_id == _Message.id)
                .where(
                    _Feedback.workspace_id == profile.workspace_id,
                    _Feedback.score <= 2,
                )
                .order_by(_Feedback.created_at.desc())
                .limit(20)
            ).all()

            if not rows:
                logger.info('[EvolveTask] No low-scored feedback for agent %s — skipping', agent_id)
                return {'status': 'no_weak_feedback', 'agent_id': agent_id}

            # Only pass assistant turns — those are what the user rated poorly
            feedback_items = [row.content for row in rows if row.role == 'assistant']
            if not feedback_items:
                logger.info('[EvolveTask] No assistant messages in low-scored feedback for agent %s', agent_id)
                return {'status': 'no_assistant_messages', 'agent_id': agent_id}

            logger.info('[EvolveTask] Running LangGraph pipeline for agent %s (%d weak items)', agent_id, len(feedback_items))

            # Hash baseline prompt before evolution
            baseline_hash = hashlib.sha256(profile.system_prompt.encode()).hexdigest()

            pipeline = _build_evolution_graph()
            result = pipeline.invoke({
                'current_prompt': profile.system_prompt,
                'feedback_items': feedback_items,
                'weaknesses': '',
                'improved_prompt': '',
            })

            improved_prompt = result.get('improved_prompt', '').strip()
            if not improved_prompt:
                logger.warning('[EvolveTask] Pipeline returned empty prompt for agent %s', agent_id)
                return {'status': 'empty_result', 'agent_id': agent_id}

            # Hash evolved prompt and verify real change occurred
            evolved_hash = hashlib.sha256(improved_prompt.encode()).hexdigest()
            if evolved_hash == baseline_hash:
                logger.info(
                    '[EvolveTask] evolution_noop for agent %s — prompt unchanged (hash=%s)',
                    agent_id, baseline_hash,
                )
                return {'status': 'evolution_noop', 'agent_id': agent_id, 'hash': baseline_hash}

            # Real change confirmed — persist new prompt and record hashes
            profile.system_prompt = improved_prompt
            profile.updated_at = datetime.utcnow()

            session.add(_EvolutionHistory(
                id=uuid.uuid4(),
                agent_profile_id=profile.id,
                fitness_score=0.0,
                notes='evolution_applied',
                recorded_at=datetime.utcnow(),
                baseline_hash=baseline_hash,
                evolved_hash=evolved_hash,
            ))
            session.commit()

        logger.info('[EvolveTask] Evolution complete for agent %s', agent_id)
        return {'status': 'evolved', 'agent_id': agent_id, 'baseline_hash': baseline_hash, 'evolved_hash': evolved_hash}

    except Exception as exc:
        logger.error('[EvolveTask] Failed for agent %s: %s', agent_id, exc, exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@app.task(name='tasks.agent_tasks.compute_fitness', bind=True, max_retries=3)
def compute_fitness(self, agent_id: str) -> dict:
    """
    Compute fitness score for an agent profile from user feedback + retention.

    Formula (V2.2 — code_copy + completion added, prior weights scaled by 0.65):
        fitness = 0.2210 * feedback_score
                + 0.0975 * weighted_correction
                + 0.0715 * session_depth_bonus
                + 0.0975 * consistency
                + 0.1625 * return_score
                + 0.2000 * code_copy_score
                + 0.1500 * completion_score

    - feedback_score:      avg(all scores) / 5  → [0, 1]
    - weighted_correction: per thumbs-down (score<=2): -0.3 if within first 2
                           messages of session, else -0.1; averaged across all
                           thumbs-down events → [-0.3, 0]
    - session_depth_bonus: fraction of sessions with >3 messages → [0, 1]
    - consistency:         fraction of sessions with at least one score>=4 → [0, 1]
    - return_score:        best retention tier achieved across workspace sessions,
                           derived from sessions.created_at (no new event needed):
                             • >=3 distinct ISO weeks of activity     → 1.00
                             • gap of 2–7 days between sessions       → 0.85
                             • next-day return (gap = 1 day)          → 0.60
                             • same-day return (>=2 sessions in a day)→ 0.25
                             • <2 sessions                            → 0.00
    - code_copy_score:     code_copy events / total assistant messages,
                           clamped to [0, 1]
    - completion_score:    completion events / total sessions, clamped to [0, 1]

    Final value is clamped to [0.0, 1.0] and rounded to 4 decimal places.
    agent_id is an AgentProfile.id (V1 has no separate agents table).
    """
    logger.info('[FitnessTask] Computing fitness for agent profile %s', agent_id)
    try:
        engine = _make_engine()
        with Session(engine) as session:
            agent_uuid = uuid.UUID(agent_id)

            # V1: agent_id IS the AgentProfile.id — no separate agents table exists
            profile = session.get(_AgentProfile, agent_uuid)

            if profile is None:
                logger.warning('[FitnessTask] No AgentProfile for agent %s', agent_id)
                return {'agent_id': agent_id, 'fitness': None, 'status': 'no_profile'}

            feedback_rows = session.execute(
                select(_Feedback.session_id, _Feedback.message_id, _Feedback.score)
                .where(_Feedback.workspace_id == profile.workspace_id)
            ).all()

            if not feedback_rows:
                logger.info('[FitnessTask] No feedback scores for agent %s', agent_id)
                return {'agent_id': agent_id, 'fitness': 0.0, 'status': 'no_data'}

            all_scores = [row.score for row in feedback_rows]

            # --- feedback_score: avg score normalized to 0-1 ---
            feedback_score = (sum(all_scores) / len(all_scores)) / 5.0

            # --- weighted_correction ---
            # Fetch all messages for sessions that have feedback, ordered by id
            # (UUID ordering is the best proxy for insertion order without a timestamp)
            feedback_session_ids = list({row.session_id for row in feedback_rows})
            message_rows = session.execute(
                select(_Message.id, _Message.session_id)
                .where(_Message.session_id.in_(feedback_session_ids))
                .order_by(_Message.session_id, _Message.id)
            ).all()

            # Build per-session ordered message-id list
            session_messages: dict[uuid.UUID, list[uuid.UUID]] = {}
            for msg in message_rows:
                session_messages.setdefault(msg.session_id, []).append(msg.id)

            correction_sum = 0.0
            correction_count = 0
            for row in feedback_rows:
                if row.score <= 2:
                    msg_list = session_messages.get(row.session_id, [])
                    try:
                        pos = msg_list.index(row.message_id) + 1  # 1-indexed
                    except ValueError:
                        pos = 99  # message not found — treat as late in session
                    correction_sum += -0.3 if pos <= 2 else -0.1
                    correction_count += 1

            weighted_correction = correction_sum / correction_count if correction_count > 0 else 0.0

            # --- session_depth_bonus: fraction of sessions with >3 messages ---
            total_sessions = len(session_messages)
            deep_sessions = sum(1 for msgs in session_messages.values() if len(msgs) > 3)
            session_depth_bonus = deep_sessions / total_sessions if total_sessions > 0 else 0.0

            # --- consistency: fraction of sessions with at least one score >= 4 ---
            sessions_with_positive = {row.session_id for row in feedback_rows if row.score >= 4}
            total_feedback_sessions = len({row.session_id for row in feedback_rows})
            consistency = (
                len(sessions_with_positive) / total_feedback_sessions
                if total_feedback_sessions > 0
                else 0.0
            )

            # --- return_score: best retention tier from sessions.created_at ---
            session_dates = session.execute(
                select(_Session.created_at)
                .where(_Session.workspace_id == profile.workspace_id)
                .where(_Session.created_at.is_not(None))
                .order_by(_Session.created_at.asc())
            ).scalars().all()

            same_day_return = False
            next_day_return = False
            seven_day_return = False
            weekly_recurring = False

            if len(session_dates) >= 2:
                iso_weeks = {
                    (d.isocalendar().year, d.isocalendar().week)
                    for d in session_dates
                }
                weekly_recurring = len(iso_weeks) >= 3

                for i in range(1, len(session_dates)):
                    gap_days = (session_dates[i].date() - session_dates[i - 1].date()).days
                    if gap_days == 0:
                        same_day_return = True
                    elif gap_days == 1:
                        next_day_return = True
                    elif 2 <= gap_days <= 7:
                        seven_day_return = True

            if weekly_recurring:
                return_score = 1.00
            elif seven_day_return:
                return_score = 0.85
            elif next_day_return:
                return_score = 0.60
            elif same_day_return:
                return_score = 0.25
            else:
                return_score = 0.00

            # --- code_copy_score: code_copy events / total assistant messages ---
            code_copy_count = session.execute(
                select(func.count(_AnalyticsEvent.id))
                .where(_AnalyticsEvent.workspace_id == profile.workspace_id)
                .where(_AnalyticsEvent.event_type == 'code_copy')
            ).scalar_one() or 0

            assistant_msg_count = session.execute(
                select(func.count(_Message.id))
                .join(_Session, _Session.id == _Message.session_id)
                .where(_Session.workspace_id == profile.workspace_id)
                .where(_Message.role == 'assistant')
            ).scalar_one() or 0

            code_copy_score = (
                min(1.0, code_copy_count / assistant_msg_count)
                if assistant_msg_count > 0 else 0.0
            )

            # --- completion_score: completion events / total sessions ---
            completion_count = session.execute(
                select(func.count(_AnalyticsEvent.id))
                .where(_AnalyticsEvent.workspace_id == profile.workspace_id)
                .where(_AnalyticsEvent.event_type == 'completion')
            ).scalar_one() or 0

            total_workspace_sessions = session.execute(
                select(func.count(_Session.id))
                .where(_Session.workspace_id == profile.workspace_id)
            ).scalar_one() or 0

            completion_score = (
                min(1.0, completion_count / total_workspace_sessions)
                if total_workspace_sessions > 0 else 0.0
            )

            # --- combine and clamp to [0.0, 1.0] ---
            # V2.2 weights: prior V2.1 weights scaled by 0.65; code_copy=0.20, completion=0.15
            fitness_raw = (
                0.2210 * feedback_score
                + 0.0975 * weighted_correction
                + 0.0715 * session_depth_bonus
                + 0.0975 * consistency
                + 0.1625 * return_score
                + 0.2000 * code_copy_score
                + 0.1500 * completion_score
            )
            fitness = round(max(0.0, min(1.0, fitness_raw)), 4)

        logger.info(
            '[FitnessTask] Agent %s fitness=%.4f (n=%d, feedback_score=%.4f, '
            'weighted_correction=%.4f, session_depth_bonus=%.4f, consistency=%.4f, '
            'return_score=%.4f, code_copy_score=%.4f, completion_score=%.4f)',
            agent_id, fitness, len(all_scores),
            feedback_score, weighted_correction, session_depth_bonus, consistency,
            return_score, code_copy_score, completion_score,
        )
        return {
            'agent_id': agent_id,
            'fitness': fitness,
            'status': 'ok',
            'n': len(all_scores),
            'components': {
                'feedback_score': round(feedback_score, 4),
                'weighted_correction': round(weighted_correction, 4),
                'session_depth_bonus': round(session_depth_bonus, 4),
                'consistency': round(consistency, 4),
                'return_score': round(return_score, 4),
                'code_copy_score': round(code_copy_score, 4),
                'completion_score': round(completion_score, 4),
            },
        }

    except Exception as exc:
        logger.error('[FitnessTask] Failed for agent %s: %s', agent_id, exc, exc_info=True)
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


@app.task(name='tasks.agent_tasks.check_evolution_triggers', bind=True, max_retries=3)
def check_evolution_triggers(self, fitness_result: dict) -> dict:
    """
    Decide whether to trigger evolution for a single agent, based on two signals:

    Fitness trigger:
        Evolve if fitness_score < 0.55 for the last 2 consecutive daily snapshots
        (stored in evolution_history).

    Interaction trigger:
        Evolve if interactions_since_evolution >= 50 AND the workspace has >= 3
        feedback records since the last evolution.

    Rate limit:
        At most one evolve_agent call per workspace per 24 hours.

    This task is designed to be the second step in a Celery chain after
    compute_fitness, so it receives the fitness result dict as its first argument.
    """
    agent_id: str = fitness_result.get('agent_id', '')
    fitness_score = fitness_result.get('fitness')  # None means no data / error

    if not agent_id:
        logger.warning('[TriggerTask] fitness_result missing agent_id — skipping')
        return {'status': 'missing_agent_id'}

    try:
        engine = _make_engine()
        _ensure_schema(engine)

        with Session(engine) as session:
            agent_uuid = uuid.UUID(agent_id)

            profile = session.get(_AgentProfile, agent_uuid)
            if profile is None:
                logger.warning('[TriggerTask] No AgentProfile for agent %s', agent_id)
                return {'status': 'no_profile', 'agent_id': agent_id}

            now = datetime.utcnow()

            # --- Rate limit: skip if already evolved in the last 24 hours ---
            if profile.last_evolution_at is not None:
                hours_since = (now - profile.last_evolution_at).total_seconds() / 3600
                if hours_since < 24:
                    logger.info(
                        '[TriggerTask] Rate-limited agent %s — last evolution %.1fh ago',
                        agent_id, hours_since,
                    )
                    return {'status': 'rate_limited', 'agent_id': agent_id, 'hours_since': hours_since}

            # --- Record today's fitness score in evolution_history (if valid) ---
            if fitness_score is not None:
                session.add(_EvolutionHistory(
                    id=uuid.uuid4(),
                    agent_profile_id=agent_uuid,
                    fitness_score=fitness_score,
                    recorded_at=now,
                ))
                session.flush()

            # --- Fitness trigger: last 2 snapshots both below 0.55 ---
            fitness_trigger = False
            recent_scores = session.execute(
                select(_EvolutionHistory.fitness_score)
                .where(_EvolutionHistory.agent_profile_id == agent_uuid)
                .order_by(_EvolutionHistory.recorded_at.desc())
                .limit(2)
            ).scalars().all()

            if len(recent_scores) >= 2 and all(s < 0.55 for s in recent_scores):
                fitness_trigger = True
                logger.info(
                    '[TriggerTask] Fitness trigger for agent %s — scores=%s',
                    agent_id, recent_scores,
                )

            # --- Interaction trigger: interactions >= 50 AND feedback >= 3 ---
            interaction_trigger = False
            interactions = profile.interactions_since_evolution or 0

            since_dt = profile.last_evolution_at  # None → count all feedback
            feedback_query = select(func.count(_Feedback.id)).where(
                _Feedback.workspace_id == profile.workspace_id
            )
            if since_dt is not None:
                feedback_query = feedback_query.where(_Feedback.created_at >= since_dt)
            feedback_since_evolution = session.execute(feedback_query).scalar_one()

            if interactions >= 50 and feedback_since_evolution >= 3:
                interaction_trigger = True
                logger.info(
                    '[TriggerTask] Interaction trigger for agent %s — interactions=%d, feedback=%d',
                    agent_id, interactions, feedback_since_evolution,
                )

            # --- Dispatch evolution if any trigger fired ---
            if fitness_trigger or interaction_trigger:
                profile.last_evolution_at = now
                profile.interactions_since_evolution = 0
                session.commit()

                evolve_agent.delay(agent_id)
                logger.info(
                    '[TriggerTask] Evolution dispatched for agent %s '
                    '(fitness_trigger=%s, interaction_trigger=%s)',
                    agent_id, fitness_trigger, interaction_trigger,
                )
                return {
                    'status': 'evolution_dispatched',
                    'agent_id': agent_id,
                    'fitness_trigger': fitness_trigger,
                    'interaction_trigger': interaction_trigger,
                }

            session.commit()  # persist evolution_history row even when no trigger
            logger.info('[TriggerTask] No trigger for agent %s', agent_id)
            return {
                'status': 'no_trigger',
                'agent_id': agent_id,
                'fitness_trigger': fitness_trigger,
                'interaction_trigger': interaction_trigger,
                'interactions': interactions,
                'feedback_since_evolution': feedback_since_evolution,
            }

    except Exception as exc:
        logger.error('[TriggerTask] Failed for agent %s: %s', agent_id, exc, exc_info=True)
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


@app.task(name='tasks.agent_tasks.nightly_fitness_beat')
def nightly_fitness_beat() -> dict:
    """
    Nightly orchestration task (run via Celery Beat at 02:00 UTC).

    For every agent profile:
    1. Recompute interactions_since_evolution from DB (messages since last evolution).
    2. Dispatch a Celery chain: compute_fitness → check_evolution_triggers.

    The chain passes the fitness result dict directly into check_evolution_triggers,
    so no intermediate storage is needed.
    """
    logger.info('[NightlyBeat] Starting nightly fitness sweep')

    engine = _make_engine()
    _ensure_schema(engine)

    with Session(engine) as session:
        profiles = session.execute(select(_AgentProfile)).scalars().all()

        if not profiles:
            logger.info('[NightlyBeat] No agent profiles found — nothing to do')
            return {'status': 'no_profiles', 'dispatched': 0}

        dispatched = 0
        for profile in profiles:
            agent_id = str(profile.id)

            # Count messages in workspace sessions since the last evolution
            # (all messages if agent has never evolved)
            msg_query = (
                select(func.count(_Message.id))
                .join(_Session, _Session.id == _Message.session_id)
                .where(_Session.workspace_id == profile.workspace_id)
            )
            if profile.last_evolution_at is not None:
                msg_query = msg_query.where(
                    _Message.created_at >= profile.last_evolution_at
                )
            interactions = session.execute(msg_query).scalar_one() or 0

            # Persist updated interaction count before dispatching
            profile.interactions_since_evolution = interactions

        session.commit()

        # Collect IDs after committing to avoid holding the DB connection
        agent_ids = [str(p.id) for p in profiles]
        workspace_ids = [str(p.workspace_id) for p in profiles]

    # Set maintenance mode ON for all workspaces (TTL 7200 = 2h auto-fallback)
    r = _get_redis()
    for ws_id in workspace_ids:
        r.set(f'maintenance:{ws_id}', 'true', ex=7200)
    logger.info('[NightlyBeat] Maintenance mode set for %d workspaces', len(workspace_ids))

    for agent_id in agent_ids:
        chain(
            compute_fitness.s(agent_id),
            check_evolution_triggers.s(),
        ).delay()
        dispatched += 1

    logger.info('[NightlyBeat] Dispatched %d fitness chains', dispatched)
    return {'status': 'ok', 'dispatched': dispatched}


@app.task(name='tasks.agent_tasks.clear_maintenance_mode')
def clear_maintenance_mode() -> dict:
    """
    Clear maintenance mode for all workspaces (run via Celery Beat at 01:00 UTC).

    Sets maintenance:{workspace_id} = 'false' with TTL 3600 so the frontend
    knows evolution completed and can show the "evolved" message until 02:00 UTC.
    """
    logger.info('[ClearMaintenance] Clearing maintenance mode for all workspaces')

    engine = _make_engine()
    _ensure_schema(engine)

    with Session(engine) as session:
        profiles = session.execute(select(_AgentProfile)).scalars().all()
        workspace_ids = [str(p.workspace_id) for p in profiles]

    if not workspace_ids:
        logger.info('[ClearMaintenance] No workspaces found — nothing to clear')
        return {'status': 'no_workspaces', 'cleared': 0}

    r = _get_redis()
    for ws_id in workspace_ids:
        r.set(f'maintenance:{ws_id}', 'false', ex=3600)

    logger.info('[ClearMaintenance] Cleared maintenance for %d workspaces', len(workspace_ids))
    return {'status': 'ok', 'cleared': len(workspace_ids)}


@app.task(name='tasks.agent_tasks.write_session_memories', bind=True, max_retries=2)
def write_session_memories(self, workspace_id: str, session_id: str, messages: list) -> dict:
    """
    Extract and persist memories from a chat exchange to agent_memories table.

    Triggered fire-and-forget from chat/router.py after each response is committed.

    Args:
        workspace_id: UUID string of the workspace
        session_id:   UUID string of the session (used to fetch full history for frequency scoring)
        messages:     current exchange — [{"role": "user"|"assistant", "content": "..."}]

    Extracts four memory types:
        preference — coding language / framework the user prefers
        fact       — project name, tech stack, repo, or team context
        pattern    — recurring problem or approach the user applies
        goal       — what the user is building or trying to achieve

    importance_score: 0.5 + 0.5 * (keyword_hits_in_session / max_keyword_hits), clamped [0.5, 1.0]
    The more often a topic appears across the session, the higher its importance.
    """
    if not messages:
        return {'status': 'no_messages'}

    try:
        engine = _make_engine()
        session_uuid = uuid.UUID(session_id)
        ws_uuid = uuid.UUID(workspace_id)

        with Session(engine) as db:
            # Resolve agent profile (agent_memories.workspace_id is FK → agent_profiles.id)
            profile = db.execute(
                select(_AgentProfile).where(_AgentProfile.workspace_id == ws_uuid)
            ).scalar_one_or_none()

            if profile is None:
                logger.warning('[MemoryTask] No AgentProfile for workspace %s', workspace_id)
                return {'status': 'no_profile', 'workspace_id': workspace_id}

            # 1. Save current exchange to mem0 vector store (best-effort)
            try:
                _mem0_save_sync(workspace_id, messages, str(profile.id))
            except Exception as mem_err:
                logger.warning('[MemoryTask] mem0 save skipped: %s', mem_err)

            # 2. Fetch all session messages for topic frequency analysis
            all_msgs = db.execute(
                select(_Message)
                .where(_Message.session_id == session_uuid)
                .order_by(_Message.created_at)
            ).scalars().all()

            full_text_lower = ' '.join(m.content for m in all_msgs).lower()

            # 3. Build session excerpt from current exchange for LLM (capped per message)
            session_excerpt = '\n'.join(
                f'{m["role"].upper()}: {m["content"][:600]}'
                for m in messages
            )

            # 4. LLM extraction of typed memory candidates
            llm = _evolution_llm(temperature=0, max_tokens=512)
            extraction_prompt = (
                'Analyze this coding assistant conversation exchange.\n\n'
                f'Exchange:\n{session_excerpt}\n\n'
                'Return a JSON array of memory objects. Each must have:\n'
                '  "memory_type": one of "fact"|"preference"|"goal"|"pattern"\n'
                '  "content": one concise sentence (max 150 chars)\n'
                '  "topic_keyword": single lowercase word for the topic\n\n'
                'Extract:\n'
                '  preference — coding language or framework the user prefers\n'
                '  fact       — project name, tech stack, repo, or team context\n'
                '  pattern    — recurring problem or approach the user applies\n'
                '  goal       — what the user is building or trying to achieve\n\n'
                'Return ONLY a valid JSON array. Return [] if nothing meaningful.\n'
                'Example: [{"memory_type":"preference","content":"User prefers TypeScript over JavaScript","topic_keyword":"typescript"}]'
            )

            candidates = []
            try:
                raw = llm.invoke([HumanMessage(content=extraction_prompt)]).content.strip()
                # Strip markdown code fences if the model wraps the JSON
                if raw.startswith('```'):
                    parts = raw.split('```')
                    raw = parts[1].lstrip('json').strip() if len(parts) > 1 else '[]'
                candidates = json.loads(raw)
                if not isinstance(candidates, list):
                    candidates = []
            except Exception as parse_err:
                logger.warning('[MemoryTask] LLM extraction failed: %s', parse_err)

            if not candidates:
                logger.info('[MemoryTask] No memories extracted for session %s', session_id)
                return {'status': 'no_memories_extracted', 'session_id': session_id}

            # 5. Topic frequency in full session text → importance_score
            topic_counts = {
                c.get('topic_keyword', '').lower(): full_text_lower.count(c.get('topic_keyword', '').lower())
                for c in candidates
                if c.get('topic_keyword', '').strip()
            }
            max_count = max(topic_counts.values(), default=1) or 1

            # 6. Load existing memory contents to skip duplicates
            existing = set(
                row[0] for row in db.execute(
                    select(_AgentMemory.content)
                    .where(_AgentMemory.workspace_id == profile.id)
                ).all()
            )

            inserted = 0
            for c in candidates:
                content = c.get('content', '').strip()
                memory_type = c.get('memory_type', 'fact')
                kw = c.get('topic_keyword', '').lower().strip()

                if not content or memory_type not in ('fact', 'preference', 'goal', 'pattern'):
                    continue
                if content in existing:
                    continue

                freq = topic_counts.get(kw, 1)
                importance = round(min(1.0, max(0.5, 0.5 + 0.5 * (freq / max_count))), 4)

                # Generate embedding for multilingual semantic search
                embedding = _embed_text_sync(content)

                db.add(_AgentMemory(
                    id=uuid.uuid4(),
                    workspace_id=profile.id,
                    memory_type=memory_type,
                    content=content,
                    importance_score=importance,
                    embedding=embedding,
                    created_at=datetime.utcnow(),
                ))
                existing.add(content)
                inserted += 1

            db.commit()

        logger.info(
            '[MemoryTask] workspace=%s session=%s inserted=%d memories',
            workspace_id, session_id, inserted,
        )
        return {
            'status': 'ok',
            'workspace_id': workspace_id,
            'session_id': session_id,
            'inserted': inserted,
        }

    except Exception as exc:
        logger.error(
            '[MemoryTask] workspace=%s session=%s error: %s',
            workspace_id, session_id, exc, exc_info=True,
        )
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


@app.task(name='tasks.agent_tasks.send_idea_reminder', bind=True, max_retries=2)
def send_idea_reminder(self, session_id: str, text: str) -> dict:
    """
    Injects a reminder message into a chat session after the countdown expires.

    Dispatched by POST /api/v1/workspaces/{id}/ideas/remind with a `countdown`
    so the Celery ETA fires after the user-selected delay (15m / 1h / 12h / 24h).

    Writes a single assistant-role message so it appears naturally in chat history
    when the user next opens that session.
    """
    try:
        engine = _make_engine()
        sess_uuid = uuid.UUID(session_id)
        content = f'💡 Reminder: {text} — still relevant?'

        with Session(engine) as db:
            # Verify session exists before inserting
            exists = db.execute(
                select(_Session.id).where(_Session.id == sess_uuid)
            ).scalar_one_or_none()
            if exists is None:
                logger.warning('[IdeaReminder] Session %s not found — skipping', session_id)
                return {'status': 'session_not_found', 'session_id': session_id}

            db.add(_Message(
                id=uuid.uuid4(),
                session_id=sess_uuid,
                role='assistant',
                content=content,
                created_at=datetime.utcnow(),
            ))
            db.commit()

        logger.info('[IdeaReminder] Injected reminder into session %s', session_id)
        return {'status': 'ok', 'session_id': session_id}

    except Exception as exc:
        logger.error('[IdeaReminder] Failed for session %s: %s', session_id, exc, exc_info=True)
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


@app.task(name='tasks.agent_tasks.run_evolution', bind=True, max_retries=3)
def run_evolution(self, workspace_id: str) -> dict:
    """
    On-demand evolution for a workspace, triggered via the API.

    Redis status lifecycle (key: evolution_status:{workspace_id}, TTL 24h):
        queued  → set by the API before dispatching this task
        running → set when this task starts
        done    → set on success
        failed  → set on error / exhausted retries
    """
    r = _get_redis()
    try:
        r.set(f'evolution_status:{workspace_id}', 'running', ex=86400)
        logger.info('[RunEvolution] Starting evolution for workspace %s', workspace_id)

        engine = _make_engine()
        _ensure_schema(engine)

        with Session(engine) as session:
            ws_uuid = uuid.UUID(workspace_id)
            profile = session.execute(
                select(_AgentProfile).where(_AgentProfile.workspace_id == ws_uuid)
            ).scalar_one_or_none()

        if profile is None:
            logger.warning('[RunEvolution] No AgentProfile for workspace %s', workspace_id)
            r.set(f'evolution_status:{workspace_id}', 'failed', ex=86400)
            return {'status': 'no_profile', 'workspace_id': workspace_id}

        result = evolve_agent.apply(args=[str(profile.id)])
        outcome = result.result if hasattr(result, 'result') else result

        r.set(f'evolution_status:{workspace_id}', 'done', ex=86400)
        logger.info('[RunEvolution] Evolution complete for workspace %s', workspace_id)
        return {'status': 'done', 'workspace_id': workspace_id, 'result': outcome}

    except Exception as exc:
        logger.error('[RunEvolution] Failed for workspace %s: %s', workspace_id, exc, exc_info=True)
        r.set(f'evolution_status:{workspace_id}', 'failed', ex=86400)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


# ---------------------------------------------------------------------------
# Champion/Challenger evaluation helpers
# ---------------------------------------------------------------------------

_CHALLENGER_THRESHOLD = 0.05


def _compute_variant_score(
    session: Session,
    workspace_id: uuid.UUID,
    variant: str,
    since: datetime,
) -> tuple[float, dict]:
    """
    Compute a composite fitness signal for one variant (champion or challenger)
    using events that occurred since the challenger was started.

    Signal weights:
        0.40 * feedback_score    (avg feedback / 5, sessions tied to this variant)
        0.30 * code_copy_score   (code_copy events / assistant messages, clamped [0,1])
        0.30 * completion_score  (completion events / sessions for this variant, clamped [0,1])

    Returns (score: float, components: dict).
    """
    # Collect session_ids associated with this variant via analytics_events
    variant_session_rows = session.execute(
        select(_AnalyticsEvent.session_id)
        .where(
            _AnalyticsEvent.workspace_id == workspace_id,
            _AnalyticsEvent.session_id.is_not(None),
            _AnalyticsEvent.created_at >= since,
            _AnalyticsEvent.event_metadata['variant'].astext == variant,
        )
        .distinct()
    ).scalars().all()

    variant_session_ids = [s for s in variant_session_rows if s]

    # --- feedback_score ---
    feedback_avg = 0.0
    if variant_session_ids:
        fb_rows = session.execute(
            select(_Feedback.score)
            .where(
                _Feedback.workspace_id == workspace_id,
                _Feedback.session_id.in_(variant_session_ids),
                _Feedback.created_at >= since,
            )
        ).scalars().all()
        if fb_rows:
            feedback_avg = sum(fb_rows) / len(fb_rows) / 5.0

    # --- code_copy_score ---
    code_copy_count = session.execute(
        select(func.count(_AnalyticsEvent.id))
        .where(
            _AnalyticsEvent.workspace_id == workspace_id,
            _AnalyticsEvent.event_type == 'code_copy',
            _AnalyticsEvent.created_at >= since,
            _AnalyticsEvent.event_metadata['variant'].astext == variant,
        )
    ).scalar_one() or 0

    assistant_msg_count = 0
    if variant_session_ids:
        assistant_msg_count = session.execute(
            select(func.count(_Message.id))
            .join(_Session, _Session.id == _Message.session_id)
            .where(
                _Session.workspace_id == workspace_id,
                _Message.session_id.in_(variant_session_ids),
                _Message.role == 'assistant',
            )
        ).scalar_one() or 0

    code_copy_score = (
        min(1.0, code_copy_count / assistant_msg_count)
        if assistant_msg_count > 0 else 0.0
    )

    # --- completion_score ---
    completion_count = session.execute(
        select(func.count(_AnalyticsEvent.id))
        .where(
            _AnalyticsEvent.workspace_id == workspace_id,
            _AnalyticsEvent.event_type == 'completion',
            _AnalyticsEvent.created_at >= since,
            _AnalyticsEvent.event_metadata['variant'].astext == variant,
        )
    ).scalar_one() or 0

    session_count = len(variant_session_ids)
    completion_score = (
        min(1.0, completion_count / session_count)
        if session_count > 0 else 0.0
    )

    score = round(
        0.40 * feedback_avg
        + 0.30 * code_copy_score
        + 0.30 * completion_score,
        4,
    )
    components = {
        'sessions': session_count,
        'feedback_avg': round(feedback_avg, 4),
        'code_copy_score': round(code_copy_score, 4),
        'completion_score': round(completion_score, 4),
    }
    return score, components


# ---------------------------------------------------------------------------
# evaluate_challenger task
# ---------------------------------------------------------------------------

@app.task(name='tasks.agent_tasks.evaluate_challenger', bind=True, max_retries=3)
def evaluate_challenger(self) -> dict:
    """
    Nightly Champion/Challenger evaluation (run via Celery Beat at 03:00 UTC).

    For every agent_profile that has:
      - challenger_prompt IS NOT NULL
      - challenger_started_at older than 24 hours

    1. Compute per-variant fitness signal (feedback + code_copy + completion)
       for events since challenger_started_at.
    2. If challenger_score > champion_score + 0.05:
         → Promote: copy challenger_prompt into system_prompt.
         → Log to evolution_history with notes='challenger_promoted'.
       Else:
         → Retain champion. Log with notes='champion_retained'.
    3. Clear challenger_prompt, challenger_started_at (and reset active_variant
       to 'champion') regardless of outcome.
    """
    logger.info('[ChallengerEval] Starting challenger evaluation sweep')

    try:
        engine = _make_engine()
        _ensure_schema(engine)

        with Session(engine) as session:
            now = datetime.utcnow()
            cutoff = now - timedelta(hours=24)

            candidates = session.execute(
                select(_AgentProfile)
                .where(
                    _AgentProfile.challenger_prompt.is_not(None),
                    _AgentProfile.challenger_started_at.is_not(None),
                    _AgentProfile.challenger_started_at < cutoff,
                )
            ).scalars().all()

            if not candidates:
                logger.info('[ChallengerEval] No candidates to evaluate — nothing to do')
                return {'status': 'no_candidates', 'evaluated': 0}

            results = []
            for profile in candidates:
                agent_id = str(profile.id)
                since = profile.challenger_started_at

                champion_score, champion_components = _compute_variant_score(
                    session, profile.workspace_id, 'champion', since
                )
                challenger_score, challenger_components = _compute_variant_score(
                    session, profile.workspace_id, 'challenger', since
                )

                promote = challenger_score > champion_score + _CHALLENGER_THRESHOLD
                notes = 'challenger_promoted' if promote else 'champion_retained'

                logger.info(
                    '[ChallengerEval] agent=%s champion=%.4f challenger=%.4f → %s',
                    agent_id, champion_score, challenger_score, notes,
                )

                if promote:
                    profile.system_prompt = profile.challenger_prompt

                profile.challenger_prompt = None
                profile.challenger_started_at = None
                profile.active_variant = 'champion'
                profile.updated_at = now

                session.add(_EvolutionHistory(
                    id=uuid.uuid4(),
                    agent_profile_id=profile.id,
                    fitness_score=max(champion_score, challenger_score),
                    notes=notes,
                    recorded_at=now,
                ))

                results.append({
                    'agent_id': agent_id,
                    'outcome': notes,
                    'champion_score': champion_score,
                    'challenger_score': challenger_score,
                    'champion_components': champion_components,
                    'challenger_components': challenger_components,
                })

            session.commit()

        logger.info('[ChallengerEval] Evaluated %d candidates', len(results))
        return {'status': 'ok', 'evaluated': len(results), 'results': results}

    except Exception as exc:
        logger.error('[ChallengerEval] Failed: %s', exc, exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@app.task(name='tasks.agent_tasks.decay_memories')
def decay_memories() -> dict:
    """
    Nightly memory decay (run via Celery Beat at 02:30 UTC).

    Decay logic:
        - last_used_at > 30 days: importance_score × 0.80
        - last_used_at > 7 days:  importance_score × 0.95
        - importance_score < 0.2: delete the memory

    Memories with memory_type = 'goal' are never decayed (goals don't fade).
    """
    logger.info('[DecayMemories] Starting nightly memory decay')

    engine = _make_engine()
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    decayed_count = 0
    deleted_count = 0

    with Session(engine) as session:
        # Fetch all non-goal memories
        memories = session.execute(
            select(_AgentMemory)
            .where(_AgentMemory.memory_type != 'goal')
        ).scalars().all()

        for mem in memories:
            last_used = mem.last_used_at or mem.created_at or now

            # Apply decay based on staleness
            if last_used < thirty_days_ago:
                mem.importance_score = round(mem.importance_score * 0.80, 4)
                decayed_count += 1
            elif last_used < seven_days_ago:
                mem.importance_score = round(mem.importance_score * 0.95, 4)
                decayed_count += 1

            # Delete if below threshold
            if mem.importance_score < 0.2:
                session.delete(mem)
                deleted_count += 1

        session.commit()

    logger.info(
        '[DecayMemories] Complete: decayed=%d, deleted=%d',
        decayed_count, deleted_count,
    )
    return {'status': 'ok', 'decayed': decayed_count, 'deleted': deleted_count}
