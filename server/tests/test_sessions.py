"""Tests for session lifecycle."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from psycopg import AsyncConnection

from openattribution.telemetry_server.models import Session, SessionCreate, SessionEnd, SessionOutcome
from openattribution.telemetry_server.services import sessions as session_service


@pytest.mark.integration
class TestSessionService:
    """Tests for the session service layer."""

    async def test_create_session_minimal(self, conn: AsyncConnection):
        """Create session with minimal data."""
        session = await session_service.create_session(
            conn,
            SessionCreate(),
        )

        assert session.id is not None
        assert session.content_scope is None
        assert session.started_at is not None
        assert session.ended_at is None

    async def test_create_session_full(self, conn: AsyncConnection):
        """Create session with all fields."""
        data = SessionCreate(
            content_scope="my-content-collection",
            manifest_ref="did:aims:abc123",
            agent_id="shopping-agent-v1",
            external_session_id="user-session-456",
            user_context={"segments": ["premium"], "locale": "en-US"},
            prior_session_ids=[str(uuid4()), str(uuid4())],
        )

        session = await session_service.create_session(conn, data)

        assert session.content_scope == "my-content-collection"
        assert session.manifest_ref == "did:aims:abc123"
        assert session.agent_id == "shopping-agent-v1"
        assert session.external_session_id == "user-session-456"
        assert session.user_context == {"segments": ["premium"], "locale": "en-US"}
        assert len(session.prior_session_ids) == 2

    async def test_get_session(self, conn: AsyncConnection, session: Session):
        """Get session by ID."""
        retrieved = await session_service.get_session(conn, session.id)

        assert retrieved is not None
        assert retrieved.id == session.id
        assert retrieved.content_scope == session.content_scope

    async def test_get_session_not_found(self, conn: AsyncConnection):
        """Get non-existent session returns None."""
        result = await session_service.get_session(conn, uuid4())
        assert result is None

    async def test_get_session_by_external_id(self, conn: AsyncConnection, session: Session):
        """Get session by external session ID."""
        retrieved = await session_service.get_session_by_external_id(
            conn, "ext-123"
        )

        assert retrieved is not None
        assert retrieved.id == session.id

    async def test_end_session(self, conn: AsyncConnection, session: Session):
        """End session with outcome."""
        outcome = SessionOutcome(
            type="conversion",
            value_amount=4999,
            currency="USD",
            products=[uuid4()],
        )

        ended = await session_service.end_session(
            conn,
            SessionEnd(session_id=str(session.id), outcome=outcome),
        )

        assert ended is not None
        assert ended.ended_at is not None
        assert ended.outcome_type == "conversion"
        assert ended.outcome_value is not None
        assert ended.outcome_value["value_amount"] == 4999

    async def test_list_sessions_empty(self, conn: AsyncConnection):
        """List sessions when none exist."""
        sessions = await session_service.list_sessions(conn)
        assert sessions == []

    async def test_list_sessions(self, conn: AsyncConnection, session: Session):
        """List sessions returns all sessions."""
        sessions = await session_service.list_sessions(conn)
        assert len(sessions) == 1
        assert sessions[0].id == session.id

    async def test_list_sessions_filter_by_outcome(self, conn: AsyncConnection, session: Session):
        """List sessions filters by outcome type."""
        # End session with conversion
        await session_service.end_session(
            conn,
            SessionEnd(
                session_id=str(session.id),
                outcome=SessionOutcome(type="conversion"),
            ),
        )

        # Create another session without ending
        await session_service.create_session(conn, SessionCreate())

        # Filter by conversion
        sessions = await session_service.list_sessions(conn, outcome_type="conversion")
        assert len(sessions) == 1
        assert sessions[0].outcome_type == "conversion"


@pytest.mark.integration
class TestSessionAPI:
    """Tests for session API endpoints."""

    async def test_start_session_minimal(self, client: AsyncClient):
        """POST /session/start with minimal data."""
        response = await client.post("/session/start", json={})

        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        UUID(data["session_id"])  # Verify it's a valid UUID

    async def test_start_session_full(self, client: AsyncClient, sample_session_data: dict):
        """POST /session/start with all fields."""
        response = await client.post("/session/start", json=sample_session_data)

        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data

    async def test_end_session(self, client: AsyncClient):
        """POST /session/end ends the session."""
        # Start a session
        start_response = await client.post("/session/start", json={})
        session_id = start_response.json()["session_id"]

        # End the session
        response = await client.post(
            "/session/end",
            json={
                "session_id": session_id,
                "outcome": {"type": "conversion", "value_amount": 1999, "currency": "USD"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    async def test_end_session_not_found(self, client: AsyncClient):
        """POST /session/end with non-existent session."""
        response = await client.post(
            "/session/end",
            json={
                "session_id": str(uuid4()),
                "outcome": {"type": "browse"},
            },
        )

        assert response.status_code == 404

    async def test_get_internal_session(self, client: AsyncClient):
        """GET /internal/sessions/{id} returns session with events."""
        # Start a session
        start_response = await client.post("/session/start", json={})
        session_id = start_response.json()["session_id"]

        # Get session
        response = await client.get(f"/internal/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert "events" in data

    async def test_list_internal_sessions(self, client: AsyncClient):
        """GET /internal/sessions returns session list."""
        # Create a few sessions
        for _ in range(3):
            await client.post("/session/start", json={})

        response = await client.get("/internal/sessions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    async def test_health_check(self, client: AsyncClient):
        """GET /health returns ok."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
