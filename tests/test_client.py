"""Tests for OpenAttribution client."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import httpx
import pytest

from openattribution import (
    ConversationTurn,
    OpenAttributionClient,
    SessionOutcome,
    TelemetryEvent,
    UserContext,
)


@pytest.fixture
def client():
    """Create a test client."""
    return OpenAttributionClient(
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
        client = OpenAttributionClient(
            endpoint="https://api.example.com/telemetry/",
            api_key="my-key",
            timeout=60.0,
        )
        assert client.endpoint == "https://api.example.com/telemetry"
        assert client.api_key == "my-key"

    def test_client_strips_trailing_slash(self):
        """Test endpoint trailing slash is stripped."""
        client = OpenAttributionClient(
            endpoint="https://api.example.com/",
            api_key="key",
        )
        assert client.endpoint == "https://api.example.com"


class TestStartSession:
    """Tests for start_session method."""

    @pytest.mark.asyncio
    async def test_start_session_basic(self, client, mock_response):
        """Test starting a basic session."""
        session_id = uuid4()

        with patch.object(
            client.client,
            "post",
            new_callable=AsyncMock,
            return_value=mock_response({"session_id": str(session_id)}),
        ) as mock_post:
            result = await client.start_session(mix_id="test-mix")

            assert result == session_id
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://api.example.com/telemetry/session/start"
            assert call_args[1]["json"]["mix_id"] == "test-mix"

    @pytest.mark.asyncio
    async def test_start_session_with_agent(self, client, mock_response):
        """Test starting a session with agent_id."""
        session_id = uuid4()

        with patch.object(
            client.client,
            "post",
            new_callable=AsyncMock,
            return_value=mock_response({"session_id": str(session_id)}),
        ) as mock_post:
            result = await client.start_session(
                mix_id="test-mix",
                agent_id="shopping-assistant",
            )

            assert result == session_id
            call_args = mock_post.call_args
            assert call_args[1]["json"]["agent_id"] == "shopping-assistant"

    @pytest.mark.asyncio
    async def test_start_session_with_user_context(self, client, mock_response):
        """Test starting a session with user context."""
        session_id = uuid4()

        with patch.object(
            client.client,
            "post",
            new_callable=AsyncMock,
            return_value=mock_response({"session_id": str(session_id)}),
        ) as mock_post:
            result = await client.start_session(
                mix_id="test-mix",
                user_context=UserContext(
                    external_id="user_hash",
                    segments=["premium", "returning"],
                ),
            )

            assert result == session_id
            call_args = mock_post.call_args
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
            "post",
            new_callable=AsyncMock,
            return_value=mock_response({}),
        ) as mock_post:
            await client.record_event(
                session_id=session_id,
                event_type="content_retrieved",
                content_id=content_id,
            )

            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://api.example.com/telemetry/events"
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
            "post",
            new_callable=AsyncMock,
            return_value=mock_response({}),
        ) as mock_post:
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

            call_args = mock_post.call_args
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
            "post",
            new_callable=AsyncMock,
            return_value=mock_response({}),
        ) as mock_post:
            await client.record_event(
                session_id=session_id,
                event_type="content_cited",
                content_id=uuid4(),
                data={"citation_type": "direct_quote", "position": "middle"},
            )

            call_args = mock_post.call_args
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
            "post",
            new_callable=AsyncMock,
            return_value=mock_response({}),
        ) as mock_post:
            await client.record_events(session_id=session_id, events=events)

            call_args = mock_post.call_args
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
            "post",
            new_callable=AsyncMock,
            return_value=mock_response({}),
        ) as mock_post:
            await client.end_session(
                session_id=session_id,
                outcome=SessionOutcome(
                    type="conversion",
                    value_amount=4999,
                    currency="USD",
                    products=[product_id],
                ),
            )

            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://api.example.com/telemetry/session/end"
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
            "post",
            new_callable=AsyncMock,
            return_value=mock_response({}),
        ) as mock_post:
            await client.end_session(
                session_id=session_id,
                outcome=SessionOutcome(type="browse"),
            )

            call_args = mock_post.call_args
            outcome = call_args[1]["json"]["outcome"]
            assert outcome["type"] == "browse"


class TestContextManager:
    """Tests for async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_response):
        """Test client works as async context manager."""
        session_id = uuid4()

        async with OpenAttributionClient(
            endpoint="https://api.example.com/telemetry",
            api_key="test-key",
        ) as client:
            with patch.object(
                client.client,
                "post",
                new_callable=AsyncMock,
                return_value=mock_response({"session_id": str(session_id)}),
            ):
                result = await client.start_session(mix_id="test")
                assert result == session_id


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_http_error_raised(self, client):
        """Test HTTP errors are raised."""
        error_response = httpx.Response(
            status_code=401,
            json={"error": "Unauthorized"},
            request=httpx.Request("POST", "https://api.example.com"),
        )

        with patch.object(
            client.client,
            "post",
            new_callable=AsyncMock,
            return_value=error_response,
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await client.start_session(mix_id="test")
