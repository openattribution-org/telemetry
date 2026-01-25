"""Session routes - public API matching the SDK."""

from fastapi import APIRouter, HTTPException

from openattribution.telemetry_server.database import Pool
from openattribution.telemetry_server.models import SessionCreate, SessionEnd
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
