import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import TypedDict

import redis as redis_sync
from celery import chain
from dotenv import load_dotenv
from sqlalchemy import create_engine, func, select, text, String, Text, DateTime, Float
from sqlalchemy.orm import Session, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from tasks import app

load_dotenv()

logger = logging.getLogger(__name__)

_DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+asyncpg://agentevo:agentevo_secret@postgres:5432/agentevo_db',
).replace('postgresql+asyncpg://', 'postgresql+psycopg2://')

_EVOLUTION_MODEL = os.getenv('EVOLUTION_MODEL', 'claude-haiku-4-5-20251001')

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
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class _EvolutionHistory(_Base):
    """Daily fitness snapshots used for the consecutive-low-score trigger."""
    __tablename__ = 'evolution_history'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    fitness_score: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


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
    llm = ChatAnthropic(model=_EVOLUTION_MODEL, temperature=0, max_tokens=1024)

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
    llm = ChatAnthropic(model=_EVOLUTION_MODEL, temperature=0.3, max_tokens=2048)

    prompt = (
        'You are an expert at writing system prompts for AI coding assistants.\n\n'
        f'Current system prompt:\n{state["current_prompt"]}\n\n'
        f'Identified weaknesses to address:\n{state["weaknesses"]}\n\n'
        'Write an improved system prompt that:\n'
        '1. Preserves everything working well in the current prompt\n'
        '2. Specifically addresses each identified weakness\n'
        '3. Keeps the same structure, tone, and agent identity (AgentEvo AI)\n'
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

            profile.system_prompt = improved_prompt
            profile.updated_at = datetime.utcnow()
            session.commit()

        logger.info('[EvolveTask] Evolution complete for agent %s', agent_id)
        return {'status': 'evolved', 'agent_id': agent_id}

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
