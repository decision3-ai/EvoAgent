from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', case_sensitive=True)

    APP_ENV: str = 'development'
    SECRET_KEY: str = 'change-me-in-production'

    DATABASE_URL: str = (
        'postgresql+asyncpg://agentevo:agentevo_secret@postgres:5432/agentevo_db'
    )
    REDIS_URL: str = 'redis://redis:6379/0'

    OPENAI_API_KEY: str = ''
    ANTHROPIC_API_KEY: str = ''

    ALLOWED_ORIGINS: List[str] = [
        'http://localhost:3000',
        'https://evoagent.io',
        'https://www.evoagent.io',
    ]
    # Override via env: ALLOWED_ORIGINS='["https://evoagent.io","https://www.evoagent.io"]'

    @property
    def is_dev(self) -> bool:
        return self.APP_ENV == 'development'


settings = Settings()
