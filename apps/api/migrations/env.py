from logging.config import fileConfig

from sqlalchemy import pool, create_engine

from alembic import context

# Import Base and all models so autogenerate can detect them
from app.core.database import Base
import app.agents.models  # noqa: F401
import app.workspaces.models  # noqa: F401
import app.auth.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    from app.core.config import settings
    # App uses asyncpg; Alembic needs a synchronous driver (psycopg2)
    return settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql+psycopg2://')


def get_async_url() -> str:
    from app.core.config import settings
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
