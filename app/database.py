from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.db_url,
    echo=False,
    connect_args={"check_same_thread": False, "timeout": 5},
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def _has_alembic_version() -> bool:
    """Return True if the alembic_version table exists in the database."""
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='alembic_version'")
        )
        return result.scalar() > 0


async def _has_podcasts_table() -> bool:
    """Return True if the podcasts table already exists (pre-Alembic install)."""
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='podcasts'")
        )
        return result.scalar() > 0


def _alembic_stamp(revision: str) -> None:
    from alembic import command
    from alembic.config import Config
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", settings.db_url.replace("+aiosqlite", ""))
    command.stamp(cfg, revision)


def _alembic_upgrade_head() -> None:
    from alembic import command
    from alembic.config import Config
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", settings.db_url.replace("+aiosqlite", ""))
    command.upgrade(cfg, "head")


async def init_db() -> None:
    """Initialize database: create tables for new installs, run migrations for existing ones."""
    import asyncio
    from app.models import podcast, episode, template, job, preferences  # noqa: F401 — register models

    if not await _has_alembic_version():
        if not await _has_podcasts_table():
            # Fresh install: create full schema, then stamp at head (no migrations needed).
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            await asyncio.to_thread(_alembic_stamp, "head")
        else:
            # Pre-Alembic install: tables exist but lack columns added in migrations.
            # Stamp at baseline then upgrade so structural migrations apply correctly.
            await asyncio.to_thread(_alembic_stamp, "0001")
            await asyncio.to_thread(_alembic_upgrade_head)
    else:
        # Alembic-managed install: apply any pending migrations.
        await asyncio.to_thread(_alembic_upgrade_head)
