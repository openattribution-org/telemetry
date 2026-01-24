"""OpenAttribution telemetry client for recording events."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx

from openattribution.telemetry.schema import (
    ConversationTurn,
    EventType,
    SessionOutcome,
    TelemetryEvent,
    UserContext,
)


class Client:
    """
    Async client for recording OpenAttribution telemetry.

    Usage:
        from openattribution.telemetry import Client, ConversationTurn, SessionOutcome

        async with Client(
            endpoint="https://api.example.com/telemetry",
            api_key="your-api-key"
        ) as client:
            session_id = await client.start_session(mix_id="my-content-mix")

            await client.record_event(
                session_id=session_id,
                event_type="content_retrieved",
                content_id=content_id
            )

            await client.record_event(
                session_id=session_id,
                event_type="turn_completed",
                turn=ConversationTurn(
                    privacy_level="intent",
                    query_intent="comparison",
                    content_ids_cited=[content_id],
                )
            )

            await client.end_session(
                session_id=session_id,
                outcome=SessionOutcome(type="conversion", value_amount=9999)
            )
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the client.

        Args:
            endpoint: Base URL for the telemetry API.
            api_key: API key for authentication.
            timeout: Request timeout in seconds.
        """
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={"X-API-Key": api_key},
        )

    async def start_session(
        self,
        mix_id: str,
        agent_id: str | None = None,
        external_session_id: str | None = None,
        user_context: UserContext | None = None,
    ) -> UUID:
        """Start a new telemetry session.

        Args:
            mix_id: ContentMix identifier (which content collection is being used).
            agent_id: Optional agent identifier (for multi-agent systems).
            external_session_id: Optional external session identifier.
            user_context: Optional user context for segmentation.

        Returns:
            Session UUID for use in subsequent calls.
        """
        response = await self.client.post(
            f"{self.endpoint}/session/start",
            json={
                "mix_id": mix_id,
                "agent_id": agent_id,
                "external_session_id": external_session_id,
                "user_context": user_context.model_dump() if user_context else {},
            },
        )
        response.raise_for_status()
        return UUID(response.json()["session_id"])

    async def record_event(
        self,
        session_id: UUID,
        event_type: EventType,
        content_id: UUID | None = None,
        product_id: UUID | None = None,
        turn: ConversationTurn | None = None,
        data: dict | None = None,
    ) -> None:
        """Record a single telemetry event.

        Args:
            session_id: Session UUID from start_session.
            event_type: Type of event (see EventType).
            content_id: Optional associated content UUID.
            product_id: Optional associated product UUID.
            turn: Optional conversation turn data (for turn_started/turn_completed).
            data: Optional additional event metadata.
        """
        event = TelemetryEvent(
            id=uuid4(),
            type=event_type,
            timestamp=datetime.now(UTC),
            content_id=content_id,
            product_id=product_id,
            turn=turn,
            data=data or {},
        )
        await self.record_events(session_id, [event])

    async def record_events(
        self,
        session_id: UUID,
        events: list[TelemetryEvent],
    ) -> None:
        """Record multiple telemetry events.

        Args:
            session_id: Session UUID from start_session
            events: List of events to record
        """
        response = await self.client.post(
            f"{self.endpoint}/events",
            json={
                "session_id": str(session_id),
                "events": [e.model_dump(mode="json") for e in events],
            },
        )
        response.raise_for_status()

    async def end_session(
        self,
        session_id: UUID,
        outcome: SessionOutcome,
    ) -> None:
        """End a session with outcome.

        Args:
            session_id: Session UUID from start_session
            outcome: Session outcome (conversion, abandonment, browse)
        """
        response = await self.client.post(
            f"{self.endpoint}/session/end",
            json={
                "session_id": str(session_id),
                "outcome": outcome.model_dump(),
            },
        )
        response.raise_for_status()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self) -> "Client":
        """Context manager entry."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Context manager exit."""
        await self.close()
