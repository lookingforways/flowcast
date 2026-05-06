from collections.abc import AsyncGenerator

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


async def init_db() -> None:
    """Create all tables and run lightweight column migrations."""
    from app.models import podcast, episode, template, job, preferences  # noqa: F401 — register models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        text = __import__("sqlalchemy", fromlist=["text"]).text
        # Add title_font column if upgrading from a pre-0.9.12 database
        try:
            await conn.execute(
                text("ALTER TABLE templates ADD COLUMN title_font VARCHAR(64) NOT NULL DEFAULT 'liberation'")
            )
        except Exception:
            pass  # column already exists
        # Add ui_font_size column if upgrading from a pre-0.9.13 database
        try:
            await conn.execute(
                text("ALTER TABLE app_preferences ADD COLUMN ui_font_size VARCHAR(8) NOT NULL DEFAULT 'L'")
            )
        except Exception:
            pass  # column already exists
        # Add ui_font_weight column if upgrading from a pre-0.9.13 database
        try:
            await conn.execute(
                text("ALTER TABLE app_preferences ADD COLUMN ui_font_weight VARCHAR(16) NOT NULL DEFAULT 'normal'")
            )
        except Exception:
            pass  # column already exists
