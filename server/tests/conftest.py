"""Pytest fixtures for OpenAttribution Telemetry Server tests."""

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

# Require TEST_DATABASE_URL for integration tests
_test_db_url = os.environ.get("TEST_DATABASE_URL")
if not _test_db_url:
    # Fall back to DATABASE_URL for simpler setups
    _test_db_url = os.environ.get("DATABASE_URL")
if _test_db_url:
    os.environ["DATABASE_URL"] = _test_db_url

from openattribution.telemetry_server.main import app  # noqa: E402
from openattribution.telemetry_server.models import Session, SessionCreate  # noqa: E402


@pytest.fixture
def anyio_backend() -> str:
    """Use asyncio backend for anyio."""
    return "asyncio"


@pytest_asyncio.fixture
async def pool() -> AsyncIterator[AsyncConnectionPool[Any]]:
    """Create a connection pool for tests."""
    from openattribution.telemetry_server.config import settings

    pool = AsyncConnectionPool(settings.database_url, open=False, min_size=1, max_size=5)
    await pool.open(wait=True, timeout=10)

    yield pool

    await pool.close()


@pytest_asyncio.fixture
async def conn(pool: AsyncConnectionPool[Any]) -> AsyncIterator[AsyncConnection]:
    """Get a connection from the pool and clean up test data."""
    async with pool.connection() as conn:
        # Clean up before test
        await conn.execute("DELETE FROM events")
        await conn.execute("DELETE FROM sessions")

        yield conn


@pytest_asyncio.fixture
async def client(pool: AsyncConnectionPool[Any]) -> AsyncIterator[AsyncClient]:
    """Create an async HTTP client for testing."""
    app.state.pool = pool

    # Clean up before tests
    async with pool.connection() as conn:
        await conn.execute("DELETE FROM events")
        await conn.execute("DELETE FROM sessions")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def session(conn: AsyncConnection) -> Session:
    """Create a test session."""
    from openattribution.telemetry_server.services import sessions as session_service

    return await session_service.create_session(
        conn,
        SessionCreate(
            content_scope="test-scope",
            agent_id="test-agent",
            external_session_id="ext-123",
            user_context={"segments": ["premium"]},
        ),
    )


@pytest.fixture
def sample_session_data() -> dict:
    """Sample session creation data."""
    return {
        "content_scope": "test-content-scope",
        "agent_id": "test-agent",
        "external_session_id": "user-abc123",
        "user_context": {"segments": ["premium", "returning"]},
    }


@pytest.fixture
def sample_event_data() -> dict:
    """Sample event data."""
    return {
        "id": str(uuid4()),
        "type": "content_retrieved",
        "timestamp": datetime.now(UTC).isoformat(),
        "content_id": str(uuid4()),
        "data": {},
    }
