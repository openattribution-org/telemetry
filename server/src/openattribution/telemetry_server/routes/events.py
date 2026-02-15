"""Event routes - public API matching the SDK."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from openattribution.telemetry_server.database import Pool
from openattribution.telemetry_server.models import EventsCreate
from openattribution.telemetry_server.services import events as event_service
from openattribution.telemetry_server.services import sessions as session_service

router = APIRouter(tags=["events"])


@router.post("/events", status_code=201)
async def record_events(
    data: EventsCreate,
    pool: Pool,
) -> dict:
    """Record one or more telemetry events for a session."""
    try:
        session_id = UUID(data.session_id)
    except ValueError as e:
        raise HTTPException(400, f"Invalid session_id: {data.session_id}") from e

    async with pool.connection() as conn:
        # Verify session exists
        session = await session_service.get_session(conn, session_id)
        if session is None:
            raise HTTPException(404, "Session not found")

        # Verify session is not ended
        if session.ended_at is not None:
            raise HTTPException(400, "Cannot add events to an ended session")

        created = await event_service.create_events(conn, session_id, data.events)
        return {"status": "ok", "events_created": len(created)}
