"""
DocuSentinel AI - Test Configuration
Shared fixtures for all backend tests.
Uses an in-memory SQLite database and mocked services.
"""

import os
import sys
import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure backend package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment variables BEFORE importing any backend modules
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key-not-real")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("UPLOAD_DIR", str(Path(__file__).parent / "tmp_uploads"))
os.environ.setdefault("VECTORSTORE_DIR", str(Path(__file__).parent / "tmp_vectorstore"))
os.environ.setdefault("DEBUG", "true")

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from backend.database import Base, get_db
from backend.main import app

# ─────────────────────────────────────────────
# In-memory test database
# ─────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Create all tables in the in-memory test database."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    """Yield a clean DB session for each test."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    """Async HTTP test client for FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def sample_txt_content() -> bytes:
    return b"""SAMPLE TEST DOCUMENT
Project Deadline: 15 November 2026
Total Contract Value: USD 1,200,000
Project Manager: Mr. John Smith
Late Payment Penalty: 2% per month
Duration: 8 months
"""


@pytest.fixture
def conflicting_txt_content() -> bytes:
    return b"""CONFLICTING TEST DOCUMENT
Project Deadline: 30 November 2026
Total Contract Value: USD 1,450,000
Project Manager: Mr. Jane Doe
Late Payment Penalty: 1.5% per month
Duration: 9.5 months
"""


@pytest.fixture
def empty_txt_content() -> bytes:
    return b""


@pytest.fixture
def tmp_upload_dir(tmp_path) -> Path:
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    return upload_dir
