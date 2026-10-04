"""
DocuSentinel AI - Database Setup

SQLAlchemy async engine + session factory for SQLite.
"""

from pathlib import Path

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase

from backend.config import get_settings

settings = get_settings()


# ---------------------------------------------------------
# Ensure the SQLite database directory exists
# ---------------------------------------------------------

database_url = settings.database_url

if database_url.startswith("sqlite"):
    # Extract SQLite file path from:
    # sqlite+aiosqlite:///./data/docusentinel.db
    db_path = database_url.split("///", 1)[-1]

    # Resolve relative path from project root
    db_file = Path(db_path)

    if not db_file.is_absolute():
        db_file = Path.cwd() / db_file

    db_file.parent.mkdir(parents=True, exist_ok=True)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------
# Database engine
# ---------------------------------------------------------

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False},
)


# ---------------------------------------------------------
# Session factory
# ---------------------------------------------------------

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------
# FastAPI database dependency
# ---------------------------------------------------------

async def get_db() -> AsyncSession:
    """FastAPI dependency: yields a database session."""

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()

        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------
# Initialize database
# ---------------------------------------------------------

async def init_db():
    """Create all tables on startup."""

    # Make absolutely sure the database directory exists
    database_url = settings.database_url

    if database_url.startswith("sqlite"):
        db_path = database_url.split("///", 1)[-1]
        db_file = Path(db_path)

        if not db_file.is_absolute():
            db_file = Path.cwd() / db_file

        db_file.parent.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)