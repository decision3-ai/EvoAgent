"""
Seed script — creates test@evoagent.io / test123456 if it doesn't exist.
Run inside the API container:
  docker exec agentevo_api_1 python seed_test_user.py
"""
import asyncio
import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.auth.models import User

EMAIL = "test@evoagent.io"
PASSWORD = "test123456"


async def seed() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == EMAIL))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"[seed] {EMAIL} already exists — nothing to do.")
        else:
            hashed = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode()
            user = User(email=EMAIL, hashed_password=hashed)
            db.add(user)
            await db.commit()
            print(f"[seed] Created test user: {EMAIL} / {PASSWORD}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
