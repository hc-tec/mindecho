import sys
import os
import asyncio
from typing import AsyncGenerator

# Add the project root to the Python path to allow imports from `app`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.main import app
from app.api import deps

# Use an on-disk SQLite database for testing to ensure shared state across connections
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_mindecho.db"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """Set up the test database once per session."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(autouse=True)
async def clean_db_between_tests():
    """Clean all tables before each test to ensure isolation and avoid UNIQUE collisions."""
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())

async def override_get_db() -> AsyncGenerator:
    """Dependency override for getting a test database session."""
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
async def db_session() -> AsyncGenerator:
    """Fixture to get a database session for direct data manipulation in tests."""
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
async def client() -> AsyncGenerator:
    """Fixture for an async test client."""
    app.dependency_overrides[deps.get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    # Clean up dependency overrides after tests
    app.dependency_overrides.clear()
