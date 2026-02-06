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
    """Create a test client with fail_silently=False (legacy behaviour)."""
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
        response = httpx.Response(
            status_code=status_code,
            json=json_data,
            request=httpx.Request("POST", "https://api.example.com"),
        )
        return response
    return _make_response


class TestClientInit:
    """Tests for client initialization."""

    def test_client_init(self):
        """Test client initializes with correct settings."""
        client = Client(
            endpoint="https://api.example.com/telemetry/",
            api_key="my-key",
            timeout=60.0,
        )
        assert client.endpoint == "https://api.example.com/telemetry"
        assert client.api_key == "my-key"

    def test_client_strips_trailing_slash(self):
        """Test endpoint trailing slash is stripped."""
        client = Client(
            endpoint="https://api.example.com/",
            api_key="key",
        )
        assert client.endpoint == "https://api.example.com"

    def test_client_defaults(self):
        """Test default values for new resilience parameters."""
        client = Client(endpoint="https://example.com", api_key="key")
        assert client.fail_silently is True
        assert client.max_retries == 3
        assert client.logger.name == "openattribution.telemetry"

    def test_client_custom_logger(self):
        """Test custom logger is used."""
        custom = logging.getLogger("custom")
        client = Client(endpoint="https://example.com", api_key="key", logger=custom)
        assert client.logger is custom


class TestStartSession:
    """Tests for start_session method."""

    @pytest.mark.asyncio
    async def test_start_session_basic(self, client, mock_response):
        """Test starting a basic session."""
        session_id = uuid4()

        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response({"session_id": str(session_id)}),
        ) as mock_req:
            result = await client.start_session(content_scope="test-mix")

            assert result == session_id
            mock_req.assert_called_once()
            call_args = mock_req.call_args
            assert call_args[0][0] == "POST"
            assert call_args[0][1] == "https://api.example.com/telemetry/session/start"
            assert call_args[1]["json"]["content_scope"] == "test-mix"

    @pytest.mark.asyncio
    async def test_start_session_without_content_scope(self, client, mock_response):
        """Test starting a session without content_scope (optional)."""
        session_id = uuid4()

        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response({"session_id": str(session_id)}),
        ) as mock_req:
            result = await client.start_session()

            assert result == session_id
            call_args = mock_req.call_args
            assert call_args[1]["json"]["content_scope"] is None

    @pytest.mark.asyncio
    async def test_start_session_with_agent(self, client, mock_response):
        """Test starting a session with agent_id."""
        session_id = uuid4()

        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response({"session_id": str(session_id)}),
        ) as mock_req:
            result = await client.start_session(
                content_scope="test-mix",
                agent_id="shopping-assistant",
            )

            assert result == session_id
            call_args = mock_req.call_args
            assert call_args[1]["json"]["agent_id"] == "shopping-assistant"

    @pytest.mark.asyncio
    async def test_start_session_with_manifest_ref(self, client, mock_response):
        """Test starting a session with AIMS manifest reference."""
        session_id = uuid4()

        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response({"session_id": str(session_id)}),
        ) as mock_req:
            result = await client.start_session(
                content_scope="test-mix",
                manifest_ref="did:aims:retailer-content-2026",
            )

            assert result == session_id
            call_args = mock_req.call_args
            assert call_args[1]["json"]["manifest_ref"] == "did:aims:retailer-content-2026"

    @pytest.mark.asyncio
    async def test_start_session_with_prior_sessions(self, client, mock_response):
        """Test starting a session with prior session IDs for journey linking."""
        session_id = uuid4()
        prior_session_1 = uuid4()
        prior_session_2 = uuid4()

        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response({"session_id": str(session_id)}),
        ) as mock_req:
            result = await client.start_session(
                content_scope="test-mix",
                prior_session_ids=[prior_session_1, prior_session_2],
            )

            assert result == session_id
            call_args = mock_req.call_args
            prior_ids = call_args[1]["json"]["prior_session_ids"]
            assert len(prior_ids) == 2
            assert str(prior_session_1) in prior_ids

    @pytest.mark.asyncio
    async def test_start_session_with_user_context(self, client, mock_response):
        """Test starting a session with user context."""
        session_id = uuid4()

        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response({"session_id": str(session_id)}),
        ) as mock_req:
            result = await client.start_session(
                content_scope="test-mix",
                user_context=UserContext(
                    external_id="user_hash",
                    segments=["premium", "returning"],
                ),
            )

            assert result == session_id
            call_args = mock_req.call_args
            user_ctx = call_args[1]["json"]["user_context"]
            assert user_ctx["external_id"] == "user_hash"
            assert "premium" in user_ctx["segments"]


class TestRecordEvent:
    """Tests for record_event method."""

    @pytest.mark.asyncio
    async def test_record_content_event(self, client, mock_response):
        """Test recording a content retrieval event."""
        session_id = uuid4()
        content_id = uuid4()

        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response({}),
        ) as mock_req:
            await client.record_event(
                session_id=session_id,
                event_type="content_retrieved",
                content_id=content_id,
            )

            mock_req.assert_called_once()
            call_args = mock_req.call_args
            assert call_args[0][0] == "POST"
            assert call_args[0][1] == "https://api.example.com/telemetry/events"
            assert call_args[1]["json"]["session_id"] == str(session_id)
            events = call_args[1]["json"]["events"]
            assert len(events) == 1
            assert events[0]["type"] == "content_retrieved"
            assert events[0]["content_id"] == str(content_id)

    @pytest.mark.asyncio
    async def test_record_turn_event(self, client, mock_response):
        """Test recording a turn_completed event with conversation data."""
        session_id = uuid4()
        content_id = uuid4()

        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response({}),
        ) as mock_req:
            await client.record_event(
                session_id=session_id,
                event_type="turn_completed",
                turn=ConversationTurn(
                    privacy_level="intent",
                    query_intent="comparison",
                    response_type="recommendation",
                    content_ids_cited=[content_id],
                    response_tokens=150,
                ),
            )

            call_args = mock_req.call_args
            events = call_args[1]["json"]["events"]
            assert events[0]["type"] == "turn_completed"
            assert events[0]["turn"]["privacy_level"] == "intent"
            assert events[0]["turn"]["query_intent"] == "comparison"

    @pytest.mark.asyncio
    async def test_record_event_with_custom_data(self, client, mock_response):
        """Test recording an event with custom data payload."""
        session_id = uuid4()

        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response({}),
        ) as mock_req:
            await client.record_event(
                session_id=session_id,
                event_type="content_cited",
                content_id=uuid4(),
                data={"citation_type": "direct_quote", "position": "middle"},
            )

            call_args = mock_req.call_args
            events = call_args[1]["json"]["events"]
            assert events[0]["data"]["citation_type"] == "direct_quote"


class TestRecordEvents:
    """Tests for record_events batch method."""

    @pytest.mark.asyncio
    async def test_record_multiple_events(self, client, mock_response):
        """Test recording multiple events in a batch."""
        session_id = uuid4()
        events = [
            TelemetryEvent(
                id=uuid4(),
                type="content_retrieved",
                timestamp=datetime.now(UTC),
                content_id=uuid4(),
            ),
            TelemetryEvent(
                id=uuid4(),
                type="content_cited",
                timestamp=datetime.now(UTC),
                content_id=uuid4(),
            ),
        ]

        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response({}),
        ) as mock_req:
            await client.record_events(session_id=session_id, events=events)

            call_args = mock_req.call_args
            sent_events = call_args[1]["json"]["events"]
            assert len(sent_events) == 2
            assert sent_events[0]["type"] == "content_retrieved"
            assert sent_events[1]["type"] == "content_cited"


class TestEndSession:
    """Tests for end_session method."""

    @pytest.mark.asyncio
    async def test_end_session_conversion(self, client, mock_response):
        """Test ending a session with conversion outcome."""
        session_id = uuid4()
        product_id = uuid4()

        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response({}),
        ) as mock_req:
            await client.end_session(
                session_id=session_id,
                outcome=SessionOutcome(
                    type="conversion",
                    value_amount=4999,
                    currency="USD",
                    products=[product_id],
                ),
            )

            mock_req.assert_called_once()
            call_args = mock_req.call_args
            assert call_args[0][1] == "https://api.example.com/telemetry/session/end"
            assert call_args[1]["json"]["session_id"] == str(session_id)
            outcome = call_args[1]["json"]["outcome"]
            assert outcome["type"] == "conversion"
            assert outcome["value_amount"] == 4999

    @pytest.mark.asyncio
    async def test_end_session_browse(self, client, mock_response):
        """Test ending a session with browse outcome (no conversion)."""
        session_id = uuid4()

        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response({}),
        ) as mock_req:
            await client.end_session(
                session_id=session_id,
                outcome=SessionOutcome(type="browse"),
            )

            call_args = mock_req.call_args
            outcome = call_args[1]["json"]["outcome"]
            assert outcome["type"] == "browse"


class TestContextManager:
    """Tests for async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_response):
        """Test client works as async context manager."""
        session_id = uuid4()

        async with Client(
            endpoint="https://api.example.com/telemetry",
            api_key="test-key",
            fail_silently=False,
            max_retries=0,
        ) as client:
            with patch.object(
                client.client,
                "request",
                new_callable=AsyncMock,
                return_value=mock_response({"session_id": str(session_id)}),
            ):
                result = await client.start_session(content_scope="test")
                assert result == session_id


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_http_error_raised(self):
        """Test HTTP errors are raised when fail_silently=False."""
        client = Client(
            endpoint="https://api.example.com/telemetry",
            api_key="test-api-key",
            fail_silently=False,
            max_retries=0,
        )
        error_response = httpx.Response(
            status_code=401,
            json={"error": "Unauthorized"},
            request=httpx.Request("POST", "https://api.example.com"),
        )

        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=error_response,
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await client.start_session(content_scope="test")

    @pytest.mark.asyncio
    async def test_silent_failure_returns_none(self, mock_response):
        """Test fail_silently=True returns None on HTTP error."""
        client = Client(
            endpoint="https://api.example.com/telemetry",
            api_key="test-api-key",
            fail_silently=True,
            max_retries=0,
        )
        error_response = mock_response({"error": "Server Error"}, status_code=500)

        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=error_response,
        ):
            result = await client.start_session(content_scope="test")
            assert result is None

    @pytest.mark.asyncio
    async def test_retry_on_503_then_succeeds(self, mock_response):
        """Test transient 503 is retried and succeeds."""
        session_id = uuid4()
        client = Client(
            endpoint="https://api.example.com/telemetry",
            api_key="test-api-key",
            fail_silently=False,
            max_retries=2,
        )
        error_resp = mock_response({}, status_code=503)
        ok_resp = mock_response({"session_id": str(session_id)})

        with (
            patch.object(
                client.client,
                "request",
                new_callable=AsyncMock,
                side_effect=[error_resp, ok_resp],
            ),
            patch("openattribution.telemetry.client.asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await client.start_session(content_scope="test")
            assert result == session_id

    @pytest.mark.asyncio
    async def test_no_retry_on_400(self, mock_response):
        """Test non-transient 400 is not retried."""
        client = Client(
            endpoint="https://api.example.com/telemetry",
            api_key="test-api-key",
            fail_silently=False,
            max_retries=3,
        )
        error_resp = mock_response({"error": "Bad Request"}, status_code=400)

        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=error_resp,
        ) as mock_req:
            with pytest.raises(httpx.HTTPStatusError):
                await client.start_session(content_scope="test")
            # Only called once — no retries for 400
            assert mock_req.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_exhaustion(self, mock_response):
        """Test retries exhaust and raise when fail_silently=False."""
        client = Client(
            endpoint="https://api.example.com/telemetry",
            api_key="test-api-key",
            fail_silently=False,
            max_retries=2,
        )
        error_resp = mock_response({}, status_code=503)

        with (
            patch.object(
                client.client,
                "request",
                new_callable=AsyncMock,
                return_value=error_resp,
            ) as mock_req,
            patch("openattribution.telemetry.client.asyncio.sleep", new_callable=AsyncMock),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await client.start_session(content_scope="test")
            # Initial attempt + 2 retries = 3 calls
            assert mock_req.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhaustion_silent(self, mock_response):
        """Test retries exhaust and return None when fail_silently=True."""
        client = Client(
            endpoint="https://api.example.com/telemetry",
            api_key="test-api-key",
            fail_silently=True,
            max_retries=2,
        )
        error_resp = mock_response({}, status_code=503)

        with (
            patch.object(
                client.client,
                "request",
                new_callable=AsyncMock,
                return_value=error_resp,
            ) as mock_req,
            patch("openattribution.telemetry.client.asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await client.start_session(content_scope="test")
            assert result is None
            assert mock_req.call_count == 3


class TestUploadSession:
    """Tests for upload_session method."""

    @pytest.mark.asyncio
    async def test_upload_session(self, client, mock_response):
        """Test uploading a complete session."""
        server_session_id = uuid4()
        caller_session_id = uuid4()

        session = TelemetrySession(
            session_id=caller_session_id,
            initiator_type="agent",
            agent_id="test-agent",
            content_scope="test-scope",
            started_at=datetime.now(UTC),
            events=[
                TelemetryEvent(
                    id=uuid4(),
                    type="content_retrieved",
                    timestamp=datetime.now(UTC),
                    content_id=uuid4(),
                ),
            ],
            outcome=SessionOutcome(type="conversion", value_amount=5000),
        )

        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response({"session_id": str(server_session_id)}),
        ) as mock_req:
            result = await client.upload_session(session)

            assert result == server_session_id
            mock_req.assert_called_once()
            call_args = mock_req.call_args
            assert call_args[0][0] == "POST"
            assert call_args[0][1] == "https://api.example.com/telemetry/session/bulk"

    @pytest.mark.asyncio
    async def test_upload_session_silent_failure(self, mock_response):
        """Test upload_session returns None on silent failure."""
        client = Client(
            endpoint="https://api.example.com/telemetry",
            api_key="test-api-key",
            fail_silently=True,
            max_retries=0,
        )
        error_resp = mock_response({"error": "fail"}, status_code=500)

        session = TelemetrySession(
            session_id=uuid4(),
            started_at=datetime.now(UTC),
        )

        with patch.object(
            client.client,
            "request",
            new_callable=AsyncMock,
            return_value=error_resp,
        ):
            result = await client.upload_session(session)
            assert result is None


class TestNoneSessionShortCircuit:
    """Tests for None session_id short-circuit behaviour."""

    @pytest.mark.asyncio
    async def test_record_event_none_session(self, silent_client):
        """Test record_event with None session_id skips HTTP call."""
        with patch.object(
            silent_client.client,
            "request",
            new_callable=AsyncMock,
        ) as mock_req:
            await silent_client.record_event(
                session_id=None,
                event_type="content_retrieved",
            )
            mock_req.assert_not_called()

    @pytest.mark.asyncio
    async def test_record_events_none_session(self, silent_client):
        """Test record_events with None session_id skips HTTP call."""
        with patch.object(
            silent_client.client,
            "request",
            new_callable=AsyncMock,
        ) as mock_req:
            await silent_client.record_events(session_id=None, events=[])
            mock_req.assert_not_called()

    @pytest.mark.asyncio
    async def test_end_session_none_session(self, silent_client):
        """Test end_session with None session_id skips HTTP call."""
        with patch.object(
            silent_client.client,
            "request",
            new_callable=AsyncMock,
        ) as mock_req:
            await silent_client.end_session(
                session_id=None,
                outcome=SessionOutcome(type="browse"),
            )
            mock_req.assert_not_called()


class TestCustomLogger:
    """Tests for custom logger receiving messages."""

    @pytest.mark.asyncio
    async def test_custom_logger_receives_failure_warning(self, mock_response):
        """Test custom logger receives warning on silent failure."""
        custom_logger = logging.getLogger("test.custom")
        client = Client(
            endpoint="https://api.example.com/telemetry",
            api_key="test-api-key",
            fail_silently=True,
            max_retries=0,
            logger=custom_logger,
        )
        error_resp = mock_response({"error": "fail"}, status_code=500)

        with (
            patch.object(
                client.client,
                "request",
                new_callable=AsyncMock,
                return_value=error_resp,
            ),
            patch.object(custom_logger, "warning") as mock_warn,
        ):
            result = await client.start_session(content_scope="test")
            assert result is None
            assert mock_warn.call_count >= 1

    @pytest.mark.asyncio
    async def test_custom_logger_receives_none_session_warning(self):
        """Test custom logger receives warning on None session_id."""
        custom_logger = logging.getLogger("test.custom2")
        client = Client(
            endpoint="https://api.example.com/telemetry",
            api_key="test-api-key",
            logger=custom_logger,
        )

        with patch.object(custom_logger, "warning") as mock_warn:
            await client.record_event(session_id=None, event_type="content_retrieved")
            mock_warn.assert_called_once()
            assert "session_id is None" in mock_warn.call_args[0][0]
