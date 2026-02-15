"""Session routes - public API matching the SDK."""

from fastapi import APIRouter, HTTPException

from openattribution.telemetry_server.database import Pool
from openattribution.telemetry_server.models import SessionCreate, SessionEnd, TelemetrySession
from openattribution.telemetry_server.services import events as event_service
from openattribution.telemetry_server.services import sessions as session_service

router = APIRouter(tags=["sessions"])


@router.post("/session/start", status_code=201)
async def start_session(
    data: SessionCreate,
    pool: Pool,
) -> dict:
    """Start a new telemetry session.

    Returns the session_id for use in subsequent calls.
    """
    async with pool.connection() as conn:
        session = await session_service.create_session(conn, data)
        return {"session_id": str(session.id)}


@router.post("/session/end")
async def end_session(
    data: SessionEnd,
    pool: Pool,
) -> dict:
    """End a session with outcome."""
    async with pool.connection() as conn:
        session = await session_service.end_session(conn, data)
        if session is None:
            raise HTTPException(404, "Session not found")
        return {"status": "ok", "session_id": str(session.id)}


@router.post("/session/bulk", status_code=201)
async def bulk_upload_session(
    data: TelemetrySession,
    pool: Pool,
) -> dict:
    """Upload a complete session (session + events + outcome) in one request.

    The server generates its own session ID; the caller's session_id is
    stored as external_session_id.
    """
    async with pool.connection() as conn:
        # Create the session
        session = await session_service.create_session(
            conn,
            SessionCreate(
                initiator_type=data.initiator_type,
                initiator=data.initiator.model_dump() if data.initiator else None,
                content_scope=data.content_scope,
                manifest_ref=data.manifest_ref,
                agent_id=data.agent_id,
                external_session_id=str(data.session_id),
                user_context=data.user_context.model_dump() if data.user_context else {},
                prior_session_ids=[str(sid) for sid in data.prior_session_ids],
            ),
        )

        response: dict = {
            "session_id": str(session.id),
            "events_created": 0,
            "outcome_recorded": False,
        }

        # Record events if provided
        if data.events:
            created = await event_service.create_events(conn, session.id, data.events)
            response["events_created"] = len(created)

        # End session with outcome if provided
        if data.outcome:
            await session_service.end_session(
                conn,
                SessionEnd(session_id=str(session.id), outcome=data.outcome),
            )
            response["outcome_recorded"] = True

        return response
