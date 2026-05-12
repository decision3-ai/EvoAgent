from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.workspaces.router import router as workspaces_router
from app.chat.router import router as chat_router
from app.agents.router import router as agents_router
from app.evolution.router import router as evolution_router
from app.auth.router import router as auth_router
from app.auth.near_router import router as near_auth_router
from app.analytics.router import router as analytics_router
from app.evosmart.router import router as evosmart_router
import app.agents.models  # noqa: F401 — registers models with SQLAlchemy metadata
import app.workspaces.models  # noqa: F401 — registers Feedback and other workspace models
import app.auth.models  # noqa: F401 — registers User model
import app.analytics.models  # noqa: F401 — registers AnalyticsEvent model


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title='evoagent.io API',
    description='AI Coding Partner — Single-agent workspace API',
    version='0.2.0',
    docs_url='/docs',
    redoc_url='/redoc',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(auth_router, prefix='/api/v1', tags=['auth'])
app.include_router(near_auth_router, prefix='/api/v1', tags=['auth'])
app.include_router(workspaces_router, prefix='/api/v1/workspaces', tags=['workspaces'])
app.include_router(chat_router, prefix='/api/v1/workspaces', tags=['chat'])
app.include_router(agents_router, prefix='/api/v1/agents', tags=['agents'])
app.include_router(evolution_router, prefix='/api/v1/evolution', tags=['evolution'])
app.include_router(analytics_router, prefix='/api/v1/events', tags=['analytics'])
app.include_router(evosmart_router, prefix='/api/v1/evosmart', tags=['evosmart'])


@app.get('/health', tags=['system'])
async def health_check() -> dict:
    return {'status': 'ok', 'service': 'evoagent-api', 'version': '0.2.0'}
