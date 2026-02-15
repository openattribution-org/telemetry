"""Event service for OpenAttribution Telemetry."""

from uuid import UUID

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from openattribution.telemetry_server.models import Event, TelemetryEvent


async def create_events(
    conn: AsyncConnection,
    session_id: UUID,
    events: list[TelemetryEvent],
) -> list[Event]:
    """Create multiple events for a session."""
    if not events:
        return []

    created_events = []
    for event in events:
        turn_data = Jsonb(event.turn.model_dump(mode="json")) if event.turn else None
        row = await conn.execute(
            """
            INSERT INTO events (
                id, session_id, event_type, content_id, product_id,
                turn_data, event_data, event_timestamp
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                event.id,
                session_id,
                event.type,
                event.content_id,
                event.product_id,
                turn_data,
                Jsonb(event.data),
                event.timestamp,
            ),
        )
        result = await row.fetchone()
        assert result is not None
        created_events.append(_row_to_event(result))

    return created_events


async def get_events_for_session(
    conn: AsyncConnection,
    session_id: UUID,
) -> list[Event]:
    """Get all events for a session, ordered by timestamp."""
    row = await conn.execute(
        """
        SELECT * FROM events
        WHERE session_id = %s
        ORDER BY event_timestamp ASC
        """,
        (session_id,),
    )
    results = await row.fetchall()
    return [_row_to_event(r) for r in results]


def _row_to_event(row: tuple) -> Event:
    """Convert a database row to an Event model."""
    return Event(
        id=row[0],
        session_id=row[1],
        event_type=row[2],
        content_id=row[3],
        product_id=row[4],
        turn_data=row[5],
        event_data=row[6] or {},
        event_timestamp=row[7],
        created_at=row[8],
    )
