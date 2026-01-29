"""Session service for OpenAttribution Telemetry."""

from datetime import UTC, datetime
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from openattribution.telemetry_server.models import (
    Session,
    SessionCreate,
    SessionEnd,
    SessionSummary,
    SessionWithEvents,
)
from openattribution.telemetry_server.services.events import get_events_for_session


async def create_session(
    conn: AsyncConnection,
    data: SessionCreate,
) -> Session:
    """Create a new telemetry session."""
    # Parse prior_session_ids to UUIDs
    prior_session_ids: list[UUID] = []
    for sid in data.prior_session_ids:
        try:
            prior_session_ids.append(UUID(sid))
        except ValueError:
            pass  # Skip invalid UUIDs

    row = await conn.execute(
        """
        INSERT INTO sessions (
            initiator_type, initiator,
            content_scope, manifest_ref,
            agent_id, external_session_id, prior_session_ids,
            user_context
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """,
        (
            data.initiator_type,
            Jsonb(data.initiator) if data.initiator else None,
            data.content_scope,
            data.manifest_ref,
            data.agent_id,
            data.external_session_id,
            prior_session_ids,
            Jsonb(data.user_context),
        ),
    )
    result = await row.fetchone()
    assert result is not None
    return _row_to_session(result)


async def get_session(
    conn: AsyncConnection,
    session_id: UUID,
) -> Session | None:
    """Get a session by ID."""
    row = await conn.execute(
        "SELECT * FROM sessions WHERE id = %s",
        (session_id,),
    )
    result = await row.fetchone()
    if result is None:
        return None
    return _row_to_session(result)


async def get_session_by_external_id(
    conn: AsyncConnection,
    external_session_id: str,
) -> Session | None:
    """Get a session by external session ID."""
    row = await conn.execute(
        "SELECT * FROM sessions WHERE external_session_id = %s ORDER BY started_at DESC LIMIT 1",
        (external_session_id,),
    )
    result = await row.fetchone()
    if result is None:
        return None
    return _row_to_session(result)


async def get_session_with_events(
    conn: AsyncConnection,
    session_id: UUID,
) -> SessionWithEvents | None:
    """Get a session with all its events."""
    session = await get_session(conn, session_id)
    if session is None:
        return None

    events = await get_events_for_session(conn, session_id)

    return SessionWithEvents(
        **session.model_dump(),
        events=events,
    )


async def end_session(
    conn: AsyncConnection,
    data: SessionEnd,
) -> Session | None:
    """End a session with outcome."""
    session_id = UUID(data.session_id)

    row = await conn.execute(
        """
        UPDATE sessions
        SET ended_at = %s,
            outcome_type = %s,
            outcome_value = %s
        WHERE id = %s
        RETURNING *
        """,
        (
            datetime.now(UTC),
            data.outcome.type,
            Jsonb(data.outcome.model_dump(mode="json")),
            session_id,
        ),
    )
    result = await row.fetchone()
    if result is None:
        return None
    return _row_to_session(result)


async def list_sessions(
    conn: AsyncConnection,
    *,
    outcome_type: str | None = None,
    content_scope: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[SessionSummary]:
    """List sessions with filters."""
    conditions = []
    params: list = []

    if outcome_type is not None:
        conditions.append("outcome_type = %s")
        params.append(outcome_type)

    if content_scope is not None:
        conditions.append("content_scope = %s")
        params.append(content_scope)

    if since is not None:
        conditions.append("ended_at >= %s")
        params.append(since)

    if until is not None:
        conditions.append("ended_at <= %s")
        params.append(until)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
        SELECT id, content_scope, external_session_id, outcome_type, started_at, ended_at
        FROM sessions
        WHERE {where_clause}
        ORDER BY started_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])

    row = await conn.execute(query, tuple(params))
    results = await row.fetchall()

    return [_row_to_session_summary(r) for r in results]


def _row_to_session(row: tuple) -> Session:
    """Convert a database row to a Session model."""
    return Session(
        id=row[0],
        initiator_type=row[1],
        initiator=row[2],
        content_scope=row[3],
        manifest_ref=row[4],
        config_snapshot_hash=row[5],
        agent_id=row[6],
        external_session_id=row[7],
        prior_session_ids=row[8] or [],
        user_context=row[9] or {},
        started_at=row[10],
        ended_at=row[11],
        outcome_type=row[12],
        outcome_value=row[13],
        created_at=row[14],
        updated_at=row[15],
    )


def _row_to_session_summary(row: tuple) -> SessionSummary:
    """Convert a database row to a SessionSummary model."""
    return SessionSummary(
        id=row[0],
        content_scope=row[1],
        external_session_id=row[2],
        outcome_type=row[3],
        started_at=row[4],
        ended_at=row[5],
    )
