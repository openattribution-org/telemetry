"""Internal routes for attribution systems."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from openattribution.telemetry_server.database import Pool
from openattribution.telemetry_server.models import Session, SessionSummary, SessionWithEvents
from openattribution.telemetry_server.services import sessions as session_service

router = APIRouter(tags=["internal"])


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: UUID,
    pool: Pool,
) -> SessionWithEvents:
    """Get a session with all its events (for attribution systems)."""
    async with pool.connection() as conn:
        session = await session_service.get_session_with_events(conn, session_id)
        if session is None:
            raise HTTPException(404, "Session not found")
        return session


@router.get("/sessions")
async def list_sessions(
    pool: Pool,
    outcome_type: Annotated[str | None, Query(description="Filter by outcome type")] = None,
    content_scope: Annotated[str | None, Query(description="Filter by content scope")] = None,
    since: Annotated[datetime | None, Query(description="Filter by ended_at >= since")] = None,
    until: Annotated[datetime | None, Query(description="Filter by ended_at <= until")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[SessionSummary]:
    """List sessions for batch processing (for attribution systems)."""
    async with pool.connection() as conn:
        return await session_service.list_sessions(
            conn,
            outcome_type=outcome_type,
            content_scope=content_scope,
            since=since,
            until=until,
            limit=limit,
            offset=offset,
        )


@router.get("/sessions/by-external-id/{external_id}")
async def get_session_by_external_id(
    external_id: str,
    pool: Pool,
) -> Session:
    """Get a session by external session ID (for journey reconstruction)."""
    async with pool.connection() as conn:
        session = await session_service.get_session_by_external_id(conn, external_id)
        if session is None:
            raise HTTPException(404, "Session not found")
        return session
