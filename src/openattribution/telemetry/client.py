"""OpenAttribution telemetry client for recording events."""

import asyncio
import logging
import random
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx

from openattribution.telemetry.schema import (
    ConversationTurn,
    EventType,
    Initiator,
    InitiatorType,
    SessionOutcome,
    TelemetryEvent,
    TelemetrySession,
    UserContext,
)

_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


class Client:
    """
    Async client for recording OpenAttribution telemetry.

    Usage:
        from openattribution.telemetry import Client, ConversationTurn, SessionOutcome

        async with Client(
            endpoint="https://api.example.com/telemetry",
            api_key="your-api-key"
        ) as client:
            session_id = await client.start_session(content_scope="my-content-mix")

            await client.record_event(
                session_id=session_id,
                event_type="content_retrieved",
                content_url="https://example.com/review"
            )

            await client.record_event(
                session_id=session_id,
                event_type="turn_completed",
                turn=ConversationTurn(
                    privacy_level="intent",
                    query_intent="comparison",
                    content_urls_cited=["https://example.com/review"],
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
        fail_silently: bool = True,
        max_retries: int = 3,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the client.

        Args:
            endpoint: Base URL for the telemetry API.
            api_key: API key for authentication.
            timeout: Request timeout in seconds.
            fail_silently: If True, catch errors and log warnings instead of raising.
            max_retries: Number of retries for transient HTTP errors.
            logger: Logger instance; defaults to ``logging.getLogger("openattribution.telemetry")``.
        """
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.fail_silently = fail_silently
        self.max_retries = max_retries
        self.logger = logger or logging.getLogger("openattribution.telemetry")
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={"X-API-Key": api_key},
        )

    async def _request(
        self,
        method: str,
        url: str,
        json: dict | None = None,
    ) -> httpx.Response | None:
        """Send an HTTP request with retry and optional silent failure.

        Retries on transient status codes (429, 500, 502, 503, 504) and
        connection/timeout errors using exponential backoff with jitter.

        Returns:
            The HTTP response, or None if ``fail_silently`` is True and the
            request failed after all retries.
        """
        last_exc: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.request(method, url, json=json)
                if response.status_code in _TRANSIENT_STATUS_CODES and attempt < self.max_retries:
                    wait = (2**attempt) + random.uniform(0, 1)  # noqa: S311
                    self.logger.warning(
                        "Transient HTTP %s from %s (attempt %d/%d), retrying in %.1fs",
                        response.status_code,
                        url,
                        attempt + 1,
                        self.max_retries + 1,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                # Non-transient HTTP error — don't retry
                break
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    wait = (2**attempt) + random.uniform(0, 1)  # noqa: S311
                    self.logger.warning(
                        "%s for %s (attempt %d/%d), retrying in %.1fs",
                        type(exc).__name__,
                        url,
                        attempt + 1,
                        self.max_retries + 1,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                break

        if self.fail_silently:
            self.logger.warning("Request to %s failed: %s", url, last_exc)
            return None
        raise last_exc  # type: ignore[misc]

    async def start_session(
        self,
        content_scope: str | None = None,
        agent_id: str | None = None,
        external_session_id: str | None = None,
        user_context: UserContext | None = None,
        manifest_ref: str | None = None,
        prior_session_ids: list[UUID] | None = None,
        initiator_type: InitiatorType = "user",
        initiator: Initiator | None = None,
    ) -> UUID | None:
        """Start a new telemetry session.

        Args:
            content_scope: Opaque content collection identifier. Implementers define
                the meaning (e.g., mix ID, AIMS manifest, API key scope).
            agent_id: Optional responding agent identifier (for multi-agent systems).
            external_session_id: Optional external session identifier.
            user_context: Optional user context for segmentation.
            manifest_ref: Optional AIMS manifest reference for licensing verification.
            prior_session_ids: Optional list of previous session IDs in the same
                user journey (for cross-session attribution).
            initiator_type: Who started the session: "user" (default) or "agent".
            initiator: Identity of the calling agent when initiator_type is "agent".

        Returns:
            Session UUID for use in subsequent calls, or None on silent failure.
        """
        response = await self._request(
            "POST",
            f"{self.endpoint}/session/start",
            json={
                "initiator_type": initiator_type,
                "initiator": initiator.model_dump() if initiator else None,
                "content_scope": content_scope,
                "agent_id": agent_id,
                "external_session_id": external_session_id,
                "user_context": user_context.model_dump() if user_context else {},
                "manifest_ref": manifest_ref,
                "prior_session_ids": [str(sid) for sid in prior_session_ids]
                if prior_session_ids
                else [],
            },
        )
        if response is None:
            return None
        return UUID(response.json()["session_id"])

    async def record_event(
        self,
        session_id: UUID | None,
        event_type: EventType,
        content_url: str | None = None,
        product_id: UUID | None = None,
        turn: ConversationTurn | None = None,
        data: dict | None = None,
    ) -> None:
        """Record a single telemetry event.

        Args:
            session_id: Session UUID from start_session.
            event_type: Type of event (see EventType).
            content_url: Optional associated content URL.
            product_id: Optional associated product UUID.
            turn: Optional conversation turn data (for turn_started/turn_completed).
            data: Optional additional event metadata.
        """
        if session_id is None:
            self.logger.warning("record_event skipped: session_id is None")
            return
        event = TelemetryEvent(
            id=uuid4(),
            type=event_type,
            timestamp=datetime.now(UTC),
            content_url=content_url,
            product_id=product_id,
            turn=turn,
            data=data or {},
        )
        await self.record_events(session_id, [event])

    async def record_events(
        self,
        session_id: UUID | None,
        events: list[TelemetryEvent],
    ) -> None:
        """Record multiple telemetry events.

        Args:
            session_id: Session UUID from start_session
            events: List of events to record
        """
        if session_id is None:
            self.logger.warning("record_events skipped: session_id is None")
            return
        await self._request(
            "POST",
            f"{self.endpoint}/events",
            json={
                "session_id": str(session_id),
                "events": [e.model_dump(mode="json") for e in events],
            },
        )

    async def end_session(
        self,
        session_id: UUID | None,
        outcome: SessionOutcome,
    ) -> None:
        """End a session with outcome.

        Args:
            session_id: Session UUID from start_session
            outcome: Session outcome (conversion, abandonment, browse)
        """
        if session_id is None:
            self.logger.warning("end_session skipped: session_id is None")
            return
        await self._request(
            "POST",
            f"{self.endpoint}/session/end",
            json={
                "session_id": str(session_id),
                "outcome": outcome.model_dump(),
            },
        )

    async def upload_session(
        self,
        session: TelemetrySession,
    ) -> UUID | None:
        """Upload a complete session in one request.

        Args:
            session: Complete TelemetrySession with events and optional outcome.

        Returns:
            Server-generated session UUID, or None on silent failure.
        """
        response = await self._request(
            "POST",
            f"{self.endpoint}/session/bulk",
            json=session.model_dump(mode="json"),
        )
        if response is None:
            return None
        return UUID(response.json()["session_id"])

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self) -> "Client":
        """Context manager entry."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Context manager exit."""
        await self.close()
