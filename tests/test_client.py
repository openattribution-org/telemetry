"""Tests for OpenAttribution telemetry client."""

import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest

from openattribution.telemetry import (
    Client,
    ConversationTurn,
    SessionOutcome,
    TelemetryEvent,
    TelemetrySession,
    UserContext,
)


@pytest.fixture
def client():
    """Create a test client with fail_silently=False."""
    return Client(
        endpoint="https://api.example.com/telemetry",
        api_key="test-api-key",
        fail_silently=False,
        max_retries=0,
    )


@pytest.fixture
def silent_client():
    """Create a test client with fail_silently=True (default)."""
    return Client(
        endpoint="https://api.example.com/telemetry",
        api_key="test-api-key",
    )


@pytest.fixture
def mock_response():
    """Create a mock HTTP response factory."""

    def _make_response(json_data: dict, status_code: int = 200):
        return httpx.Response(
            status_code=status_code,
            json=json_data,
            request=httpx.Request("POST", "https://api.example.com"),
        )

    return _make_response


class TestClientInit:
    """Tests for client initialisation."""

    def test_strips_trailing_slash(self):
        """Endpoint trailing slash is stripped."""
        c = Client(endpoint="https://api.example.com/", api_key="key")
        assert c.endpoint == "https://api.example.com"

    def test_defaults(self):
        """Default resilience settings are sensible."""
        c = Client(endpoint="https://example.com", api_key="key")
        assert c.fail_silently is True
        assert c.max_retries == 3
        assert c.logger.name == "openattribution.telemetry"

    def test_custom_logger(self):
        """Custom logger is used when provided."""
        custom = logging.getLogger("custom")
        c = Client(endpoint="https://example.com", api_key="key", logger=custom)
        assert c.logger is custom


class TestSessionLifecycle:
    """Tests for the full session lifecycle through the client."""

    @pytest.mark.asyncio
    async def test_start_session(self, client, mock_response):
        """GIVEN valid params WHEN start_session called SHOULD return session UUID."""
        session_id = uuid4()
        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response({"session_id": str(session_id)}),
        ):
            result = await client.start_session(
                content_scope="test-mix",
                agent_id="shopping-assistant",
                prior_session_ids=[uuid4()],
                user_context=UserContext(segments=["premium"]),
            )
            assert result == session_id

    @pytest.mark.asyncio
    async def test_record_event(self, client, mock_response):
        """GIVEN a session WHEN recording an event SHOULD succeed."""
        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response({}),
        ):
            await client.record_event(
                session_id=uuid4(),
                event_type="turn_completed",
                turn=ConversationTurn(
                    privacy_level="intent",
                    query_intent="comparison",
                ),
            )

    @pytest.mark.asyncio
    async def test_record_events_batch(self, client, mock_response):
        """GIVEN multiple events WHEN recording in batch SHOULD succeed."""
        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response({}),
        ):
            await client.record_events(
                session_id=uuid4(),
                events=[
                    TelemetryEvent(
                        id=uuid4(),
                        type="content_retrieved",
                        timestamp=datetime.now(UTC),
                        content_url="https://example.com/review-1",
                    ),
                    TelemetryEvent(
                        id=uuid4(),
                        type="content_cited",
                        timestamp=datetime.now(UTC),
                        content_url="https://example.com/review-2",
                    ),
                ],
            )

    @pytest.mark.asyncio
    async def test_end_session(self, client, mock_response):
        """GIVEN a session WHEN ending with outcome SHOULD succeed."""
        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response({}),
        ):
            await client.end_session(
                session_id=uuid4(),
                outcome=SessionOutcome(
                    type="conversion",
                    value_amount=4999,
                    currency="USD",
                    products=[uuid4()],
                ),
            )

    @pytest.mark.asyncio
    async def test_upload_session(self, client, mock_response):
        """GIVEN a complete session WHEN uploading in bulk SHOULD return server session ID."""
        server_session_id = uuid4()
        session = TelemetrySession(
            session_id=uuid4(),
            initiator_type="agent",
            agent_id="test-agent",
            content_scope="test-scope",
            started_at=datetime.now(UTC),
            events=[
                TelemetryEvent(
                    id=uuid4(),
                    type="content_retrieved",
                    timestamp=datetime.now(UTC),
                    content_url="https://example.com/review",
                ),
            ],
            outcome=SessionOutcome(type="conversion", value_amount=5000),
        )

        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response({"session_id": str(server_session_id)}),
        ):
            result = await client.upload_session(session)
            assert result == server_session_id

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_response):
        """Client works as async context manager."""
        session_id = uuid4()
        async with Client(
            endpoint="https://api.example.com/telemetry",
            api_key="test-key",
            fail_silently=False,
            max_retries=0,
        ) as c:
            with patch.object(
                c.client,
                "request",
                new_callable=AsyncMock,
                return_value=mock_response({"session_id": str(session_id)}),
            ):
                result = await c.start_session(content_scope="test")
                assert result == session_id


class TestErrorHandling:
    """Tests for resilience: retries, silent failure, error propagation."""

    @pytest.mark.asyncio
    async def test_http_error_raised_when_not_silent(self, mock_response):
        """GIVEN fail_silently=False WHEN HTTP 401 SHOULD raise."""
        c = Client(
            endpoint="https://api.example.com/telemetry",
            api_key="test-api-key",
            fail_silently=False,
            max_retries=0,
        )
        with patch.object(
            c.client,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response({"error": "Unauthorized"}, 401),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await c.start_session(content_scope="test")

    @pytest.mark.asyncio
    async def test_silent_failure_returns_none(self, mock_response):
        """GIVEN fail_silently=True WHEN HTTP 500 SHOULD return None."""
        c = Client(
            endpoint="https://api.example.com/telemetry",
            api_key="test-api-key",
            fail_silently=True,
            max_retries=0,
        )
        with patch.object(
            c.client,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response({"error": "Server Error"}, 500),
        ):
            result = await c.start_session(content_scope="test")
            assert result is None

    @pytest.mark.asyncio
    async def test_retry_on_503_then_succeeds(self, mock_response):
        """GIVEN transient 503 WHEN retried SHOULD succeed on second attempt."""
        session_id = uuid4()
        c = Client(
            endpoint="https://api.example.com/telemetry",
            api_key="test-api-key",
            fail_silently=False,
            max_retries=2,
        )
        with (
            patch.object(
                c.client,
                "request",
                new_callable=AsyncMock,
                side_effect=[
                    mock_response({}, 503),
                    mock_response({"session_id": str(session_id)}),
                ],
            ),
            patch("openattribution.telemetry.client.asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await c.start_session(content_scope="test")
            assert result == session_id

    @pytest.mark.asyncio
    async def test_no_retry_on_400(self, mock_response):
        """GIVEN non-transient 400 SHOULD not retry."""
        c = Client(
            endpoint="https://api.example.com/telemetry",
            api_key="test-api-key",
            fail_silently=False,
            max_retries=3,
        )
        with patch.object(
            c.client,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response({"error": "Bad Request"}, 400),
        ) as mock_req:
            with pytest.raises(httpx.HTTPStatusError):
                await c.start_session(content_scope="test")
            assert mock_req.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_exhaustion_raises(self, mock_response):
        """GIVEN persistent 503 WHEN retries exhausted SHOULD raise."""
        c = Client(
            endpoint="https://api.example.com/telemetry",
            api_key="test-api-key",
            fail_silently=False,
            max_retries=2,
        )
        with (
            patch.object(
                c.client,
                "request",
                new_callable=AsyncMock,
                return_value=mock_response({}, 503),
            ) as mock_req,
            patch("openattribution.telemetry.client.asyncio.sleep", new_callable=AsyncMock),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await c.start_session(content_scope="test")
            assert mock_req.call_count == 3  # 1 initial + 2 retries

    @pytest.mark.asyncio
    async def test_retry_exhaustion_silent_returns_none(self, mock_response):
        """GIVEN persistent 503 and fail_silently=True SHOULD return None."""
        c = Client(
            endpoint="https://api.example.com/telemetry",
            api_key="test-api-key",
            fail_silently=True,
            max_retries=2,
        )
        with (
            patch.object(
                c.client,
                "request",
                new_callable=AsyncMock,
                return_value=mock_response({}, 503),
            ),
            patch("openattribution.telemetry.client.asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await c.start_session(content_scope="test")
            assert result is None


class TestNoneSessionShortCircuit:
    """Tests for None session_id short-circuit — prevents HTTP calls after silent start failure."""

    @pytest.mark.asyncio
    async def test_record_event_none_session(self, silent_client):
        """GIVEN session_id is None SHOULD skip HTTP call."""
        with patch.object(silent_client.client, "request", new_callable=AsyncMock) as mock_req:
            await silent_client.record_event(session_id=None, event_type="content_retrieved")
            mock_req.assert_not_called()

    @pytest.mark.asyncio
    async def test_end_session_none_session(self, silent_client):
        """GIVEN session_id is None SHOULD skip HTTP call."""
        with patch.object(silent_client.client, "request", new_callable=AsyncMock) as mock_req:
            await silent_client.end_session(session_id=None, outcome=SessionOutcome(type="browse"))
            mock_req.assert_not_called()

    @pytest.mark.asyncio
    async def test_none_session_logs_warning(self):
        """GIVEN session_id is None SHOULD log a warning."""
        custom_logger = logging.getLogger("test.none_session")
        c = Client(
            endpoint="https://api.example.com/telemetry",
            api_key="test-api-key",
            logger=custom_logger,
        )
        with patch.object(custom_logger, "warning") as mock_warn:
            await c.record_event(session_id=None, event_type="content_retrieved")
            mock_warn.assert_called_once()
            assert "session_id is None" in mock_warn.call_args[0][0]
