"""Tests for event recording."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from psycopg import AsyncConnection

from openattribution.telemetry_server.models import Session, TelemetryEvent
from openattribution.telemetry_server.services import events as event_service


@pytest.mark.integration
class TestEventService:
    """Tests for the event service layer."""

    async def test_create_single_event(self, conn: AsyncConnection, session: Session):
        """Create a single event."""
        event = TelemetryEvent(
            id=uuid4(),
            type="content_retrieved",
            timestamp=datetime.now(UTC),
            content_id=uuid4(),
            data={"source": "vector_db"},
        )

        created = await event_service.create_events(conn, session.id, [event])

        assert len(created) == 1
        assert created[0].id == event.id
        assert created[0].event_type == "content_retrieved"
        assert created[0].event_data == {"source": "vector_db"}

    async def test_create_multiple_events(self, conn: AsyncConnection, session: Session):
        """Create multiple events in batch."""
        events = [
            TelemetryEvent(
                id=uuid4(),
                type="content_retrieved",
                timestamp=datetime.now(UTC),
                content_id=uuid4(),
            ),
            TelemetryEvent(
                id=uuid4(),
                type="content_displayed",
                timestamp=datetime.now(UTC),
                content_id=uuid4(),
            ),
            TelemetryEvent(
                id=uuid4(),
                type="content_cited",
                timestamp=datetime.now(UTC),
                content_id=uuid4(),
                data={
                    "citation_type": "direct_quote",
                    "excerpt_tokens": 45,
                    "position": "primary",
                },
            ),
        ]

        created = await event_service.create_events(conn, session.id, events)

        assert len(created) == 3

    async def test_create_events_empty_list(self, conn: AsyncConnection, session: Session):
        """Create with empty list returns empty."""
        created = await event_service.create_events(conn, session.id, [])
        assert created == []

    async def test_get_events_for_session(self, conn: AsyncConnection, session: Session):
        """Get events returns events ordered by timestamp."""
        t1 = datetime(2026, 1, 25, 10, 0, 0, tzinfo=UTC)
        t2 = datetime(2026, 1, 25, 10, 1, 0, tzinfo=UTC)
        t3 = datetime(2026, 1, 25, 10, 2, 0, tzinfo=UTC)

        events = [
            TelemetryEvent(id=uuid4(), type="content_retrieved", timestamp=t2),
            TelemetryEvent(id=uuid4(), type="content_cited", timestamp=t3),
            TelemetryEvent(id=uuid4(), type="turn_started", timestamp=t1),
        ]
        await event_service.create_events(conn, session.id, events)

        # Get events - should be ordered by timestamp
        retrieved = await event_service.get_events_for_session(conn, session.id)

        assert len(retrieved) == 3
        assert retrieved[0].event_type == "turn_started"
        assert retrieved[1].event_type == "content_retrieved"
        assert retrieved[2].event_type == "content_cited"


@pytest.mark.integration
class TestEventsAPI:
    """Tests for events API endpoints."""

    async def test_record_single_event(self, client: AsyncClient, sample_event_data: dict):
        """POST /events records a single event."""
        # Start a session
        start_response = await client.post("/session/start", json={})
        session_id = start_response.json()["session_id"]

        # Record event
        response = await client.post(
            "/events",
            json={
                "session_id": session_id,
                "events": [sample_event_data],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "ok"
        assert data["events_created"] == 1

    async def test_record_multiple_events(self, client: AsyncClient):
        """POST /events records multiple events."""
        # Start a session
        start_response = await client.post("/session/start", json={})
        session_id = start_response.json()["session_id"]

        events = [
            {
                "id": str(uuid4()),
                "type": "content_retrieved",
                "timestamp": datetime.now(UTC).isoformat(),
                "content_id": str(uuid4()),
            },
            {
                "id": str(uuid4()),
                "type": "content_cited",
                "timestamp": datetime.now(UTC).isoformat(),
                "content_id": str(uuid4()),
                "data": {"citation_type": "paraphrase"},
            },
        ]

        response = await client.post(
            "/events",
            json={"session_id": session_id, "events": events},
        )

        assert response.status_code == 201
        assert response.json()["events_created"] == 2

    async def test_record_events_session_not_found(
        self, client: AsyncClient, sample_event_data: dict
    ):
        """POST /events with non-existent session returns 404."""
        response = await client.post(
            "/events",
            json={
                "session_id": str(uuid4()),
                "events": [sample_event_data],
            },
        )

        assert response.status_code == 404

    async def test_record_events_session_ended(self, client: AsyncClient, sample_event_data: dict):
        """POST /events to ended session returns 400."""
        # Start and end a session
        start_response = await client.post("/session/start", json={})
        session_id = start_response.json()["session_id"]

        await client.post(
            "/session/end",
            json={
                "session_id": session_id,
                "outcome": {"type": "browse"},
            },
        )

        # Try to add events
        response = await client.post(
            "/events",
            json={
                "session_id": session_id,
                "events": [sample_event_data],
            },
        )

        assert response.status_code == 400
        assert "ended session" in response.json()["detail"].lower()

    async def test_full_session_flow(self, client: AsyncClient):
        """Test complete session flow: start -> events -> end."""
        # 1. Start session
        start_response = await client.post(
            "/session/start",
            json={
                "content_scope": "e-commerce-collection",
                "external_session_id": "user-journey-001",
                "user_context": {"segments": ["returning"]},
            },
        )
        assert start_response.status_code == 201
        session_id = start_response.json()["session_id"]

        # 2. Record content events
        content_id = str(uuid4())
        events_response = await client.post(
            "/events",
            json={
                "session_id": session_id,
                "events": [
                    {
                        "id": str(uuid4()),
                        "type": "content_retrieved",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "content_id": content_id,
                    },
                    {
                        "id": str(uuid4()),
                        "type": "content_cited",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "content_id": content_id,
                        "data": {"citation_type": "direct_quote"},
                    },
                ],
            },
        )
        assert events_response.status_code == 201

        # 3. End session with conversion
        product_id = str(uuid4())
        end_response = await client.post(
            "/session/end",
            json={
                "session_id": session_id,
                "outcome": {
                    "type": "conversion",
                    "value_amount": 9999,
                    "currency": "USD",
                    "products": [product_id],
                },
            },
        )
        assert end_response.status_code == 200

        # 4. Verify full session via internal API
        internal_response = await client.get(f"/internal/sessions/{session_id}")
        assert internal_response.status_code == 200

        session_data = internal_response.json()
        assert session_data["content_scope"] == "e-commerce-collection"
        assert session_data["outcome_type"] == "conversion"
        assert len(session_data["events"]) == 2
