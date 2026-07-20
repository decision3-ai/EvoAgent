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
    OLLAMA_BASE_URL: str = 'http://ollama:11434'

    OPENROUTER_API_KEY: str = ''
    GEMINI_API_KEY: str = ''
    DEEPSEEK_DIRECT_API_KEY: str = ''
    SERPER_API_KEY: str = ''

    JWT_SECRET_KEY: str = 'change-me-in-production'
    JWT_ALGORITHM: str = 'HS256'
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    D3RCP_BRIDGE_URL: str = ''

    NEAR_NETWORK: str = 'testnet'  # 'testnet' | 'mainnet'

    ALLOWED_ORIGINS: List[str] = [
        'http://localhost:3000',
        'https://evoagent.io',
        'https://www.evoagent.io',
        'https://agentevo-web.vercel.app',
    ]
    # Override via env: ALLOWED_ORIGINS='["https://evoagent.io","https://www.evoagent.io"]'

    @property
    def is_dev(self) -> bool:
        return self.APP_ENV == 'development'


settings = Settings()
