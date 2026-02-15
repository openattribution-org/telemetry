"""Tests for OpenAttribution telemetry schema serialisation."""

from datetime import UTC, datetime
from uuid import uuid4

from openattribution.telemetry import (
    ConversationTurn,
    SessionOutcome,
    TelemetryEvent,
    TelemetrySession,
    UserContext,
)


class TestSerialization:
    """Tests for JSON serialisation roundtrips — the wire format matters."""

    def test_session_json_roundtrip(self):
        """GIVEN a fully populated session
        WHEN serialised to JSON and restored
        SHOULD preserve all fields including nested models."""
        prior_session = uuid4()
        session = TelemetrySession(
            session_id=uuid4(),
            content_scope="test",
            manifest_ref="did:aims:test",
            prior_session_ids=[prior_session],
            started_at=datetime.now(UTC),
            events=[
                TelemetryEvent(
                    id=uuid4(),
                    type="content_retrieved",
                    timestamp=datetime.now(UTC),
                    content_id=uuid4(),
                ),
            ],
            outcome=SessionOutcome(type="browse"),
        )

        json_data = session.model_dump(mode="json")
        restored = TelemetrySession.model_validate(json_data)

        assert restored.session_id == session.session_id
        assert restored.content_scope == session.content_scope
        assert restored.manifest_ref == session.manifest_ref
        assert len(restored.prior_session_ids) == 1
        assert len(restored.events) == 1
        assert restored.outcome.type == "browse"

    def test_conversation_turn_json_roundtrip(self):
        """GIVEN a turn with intent, topics, and content IDs
        WHEN serialised to JSON and restored
        SHOULD preserve all fields."""
        turn = ConversationTurn(
            privacy_level="intent",
            query_intent="comparison",
            topics=["headphones", "wireless"],
            content_ids_retrieved=[uuid4(), uuid4()],
            content_ids_cited=[uuid4()],
            response_tokens=150,
        )

        json_data = turn.model_dump(mode="json")
        restored = ConversationTurn.model_validate(json_data)

        assert restored.privacy_level == "intent"
        assert restored.query_intent == "comparison"
        assert len(restored.topics) == 2
        assert len(restored.content_ids_retrieved) == 2

    def test_event_with_turn_json_roundtrip(self):
        """GIVEN a turn_completed event with nested ConversationTurn
        WHEN serialised to JSON and restored
        SHOULD preserve nested turn data."""
        event = TelemetryEvent(
            id=uuid4(),
            type="turn_completed",
            timestamp=datetime.now(UTC),
            turn=ConversationTurn(
                privacy_level="full",
                query_text="Test query",
                response_text="Test response",
            ),
        )

        json_data = event.model_dump(mode="json")
        restored = TelemetryEvent.model_validate(json_data)

        assert restored.turn is not None
        assert restored.turn.query_text == "Test query"


class TestCompleteSessionLifecycle:
    """Tests that the full model graph composes correctly."""

    def test_complete_session_with_all_event_types(self):
        """GIVEN a session with content, turn, commerce events and an outcome
        WHEN constructed
        SHOULD hold the complete event graph."""
        content_id = uuid4()
        product_id = uuid4()
        prior_session = uuid4()

        session = TelemetrySession(
            session_id=uuid4(),
            agent_id="test-agent",
            content_scope="test-mix",
            prior_session_ids=[prior_session],
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            user_context=UserContext(segments=["test"]),
            events=[
                TelemetryEvent(
                    id=uuid4(),
                    type="content_retrieved",
                    timestamp=datetime.now(UTC),
                    content_id=content_id,
                ),
                TelemetryEvent(
                    id=uuid4(),
                    type="content_cited",
                    timestamp=datetime.now(UTC),
                    content_id=content_id,
                    data={
                        "citation_type": "paraphrase",
                        "excerpt_tokens": 85,
                        "position": "primary",
                    },
                ),
                TelemetryEvent(
                    id=uuid4(),
                    type="turn_completed",
                    timestamp=datetime.now(UTC),
                    turn=ConversationTurn(
                        privacy_level="intent",
                        query_intent="product_research",
                        content_ids_cited=[content_id],
                    ),
                ),
                TelemetryEvent(
                    id=uuid4(),
                    type="product_viewed",
                    timestamp=datetime.now(UTC),
                    product_id=product_id,
                ),
                TelemetryEvent(
                    id=uuid4(),
                    type="checkout_completed",
                    timestamp=datetime.now(UTC),
                    data={"order_value_amount": 4999, "currency": "USD"},
                ),
            ],
            outcome=SessionOutcome(
                type="conversion",
                value_amount=4999,
                currency="USD",
                products=[product_id],
            ),
        )

        assert len(session.events) == 5
        assert session.outcome.type == "conversion"
        assert session.ended_at is not None
        assert session.prior_session_ids == [prior_session]
