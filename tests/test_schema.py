"""Tests for OpenAttribution schema models."""

from datetime import UTC, datetime
from uuid import uuid4

from openattribution import (
    ConversationTurn,
    EventType,
    IntentCategory,
    OutcomeType,
    SessionOutcome,
    TelemetryEvent,
    TelemetrySession,
    UserContext,
)


class TestEventTypes:
    """Tests for event type definitions."""

    def test_content_event_types(self):
        """Test content lifecycle event types are valid."""
        content_events: list[EventType] = [
            "content_retrieved",
            "content_displayed",
            "content_engaged",
            "content_cited",
        ]
        for event_type in content_events:
            event = TelemetryEvent(
                id=uuid4(),
                type=event_type,
                timestamp=datetime.now(UTC),
            )
            assert event.type == event_type

    def test_conversation_event_types(self):
        """Test conversation event types are valid."""
        conv_events: list[EventType] = [
            "turn_started",
            "turn_completed",
        ]
        for event_type in conv_events:
            event = TelemetryEvent(
                id=uuid4(),
                type=event_type,
                timestamp=datetime.now(UTC),
            )
            assert event.type == event_type

    def test_commerce_event_types(self):
        """Test commerce event types are valid."""
        commerce_events: list[EventType] = [
            "product_viewed",
            "product_compared",
            "cart_add",
            "cart_remove",
            "checkout_started",
            "checkout_completed",
            "checkout_abandoned",
        ]
        for event_type in commerce_events:
            event = TelemetryEvent(
                id=uuid4(),
                type=event_type,
                timestamp=datetime.now(UTC),
            )
            assert event.type == event_type


class TestUserContext:
    """Tests for UserContext model."""

    def test_user_context_defaults(self):
        """Test UserContext with default values."""
        ctx = UserContext()
        assert ctx.external_id is None
        assert ctx.segments == []
        assert ctx.attributes == {}

    def test_user_context_with_segments(self):
        """Test UserContext with segments."""
        ctx = UserContext(
            external_id="user_hash_123",
            segments=["premium", "returning", "mobile"],
            attributes={"region": "US", "tier": "gold"},
        )
        assert ctx.external_id == "user_hash_123"
        assert len(ctx.segments) == 3
        assert ctx.attributes["tier"] == "gold"


class TestConversationTurn:
    """Tests for ConversationTurn model with privacy levels."""

    def test_minimal_privacy_level(self):
        """Test ConversationTurn with minimal privacy (default)."""
        turn = ConversationTurn(
            privacy_level="minimal",
            content_ids_retrieved=[uuid4(), uuid4()],
            content_ids_cited=[uuid4()],
            query_tokens=15,
            response_tokens=150,
        )
        assert turn.privacy_level == "minimal"
        assert turn.query_text is None
        assert turn.response_text is None
        assert turn.query_intent is None
        assert len(turn.content_ids_retrieved) == 2

    def test_intent_privacy_level(self):
        """Test ConversationTurn with intent privacy level."""
        turn = ConversationTurn(
            privacy_level="intent",
            query_intent="product_research",
            response_type="recommendation",
            topics=["headphones", "noise-cancelling", "Sony"],
            content_ids_cited=[uuid4()],
            query_tokens=12,
            response_tokens=200,
            model_id="claude-3-opus",
        )
        assert turn.privacy_level == "intent"
        assert turn.query_intent == "product_research"
        assert turn.query_text is None  # Not included at intent level
        assert len(turn.topics) == 3
        assert turn.model_id == "claude-3-opus"

    def test_full_privacy_level(self):
        """Test ConversationTurn with full privacy level."""
        turn = ConversationTurn(
            privacy_level="full",
            query_text="What are the best noise-cancelling headphones?",
            response_text="Based on my research, the Sony WH-1000XM5...",
            query_intent="comparison",
            response_type="recommendation",
            topics=["headphones", "Sony", "Bose"],
            content_ids_retrieved=[uuid4(), uuid4(), uuid4()],
            content_ids_cited=[uuid4()],
            query_tokens=8,
            response_tokens=250,
        )
        assert turn.privacy_level == "full"
        assert "noise-cancelling" in turn.query_text
        assert "Sony" in turn.response_text

    def test_summary_privacy_level(self):
        """Test ConversationTurn with summary privacy level."""
        turn = ConversationTurn(
            privacy_level="summary",
            query_text="User asked about headphone recommendations",  # summarized
            response_text="Agent provided comparison of top 3 headphones",  # summarized
            query_intent="comparison",
        )
        assert turn.privacy_level == "summary"

    def test_all_intent_categories(self):
        """Test all intent categories are valid."""
        intent_categories: list[IntentCategory] = [
            "product_research",
            "comparison",
            "how_to",
            "troubleshooting",
            "general_question",
            "purchase_intent",
            "price_check",
            "availability_check",
            "review_seeking",
            "chitchat",
            "other",
        ]
        for intent in intent_categories:
            turn = ConversationTurn(
                privacy_level="intent",
                query_intent=intent,
            )
            assert turn.query_intent == intent


class TestTelemetryEvent:
    """Tests for TelemetryEvent model."""

    def test_content_event(self):
        """Test content retrieval event."""
        content_id = uuid4()
        event = TelemetryEvent(
            id=uuid4(),
            type="content_retrieved",
            timestamp=datetime.now(UTC),
            content_id=content_id,
        )
        assert event.type == "content_retrieved"
        assert event.content_id == content_id
        assert event.product_id is None
        assert event.turn is None

    def test_product_event(self):
        """Test product viewed event."""
        product_id = uuid4()
        event = TelemetryEvent(
            id=uuid4(),
            type="product_viewed",
            timestamp=datetime.now(UTC),
            product_id=product_id,
            data={"view_duration_seconds": 30},
        )
        assert event.type == "product_viewed"
        assert event.product_id == product_id
        assert event.data["view_duration_seconds"] == 30

    def test_turn_event_with_conversation_data(self):
        """Test turn_completed event with ConversationTurn."""
        content_id = uuid4()
        event = TelemetryEvent(
            id=uuid4(),
            type="turn_completed",
            timestamp=datetime.now(UTC),
            turn=ConversationTurn(
                privacy_level="intent",
                query_intent="comparison",
                response_type="recommendation",
                content_ids_cited=[content_id],
                response_tokens=150,
            ),
        )
        assert event.type == "turn_completed"
        assert event.turn is not None
        assert event.turn.query_intent == "comparison"
        assert content_id in event.turn.content_ids_cited

    def test_event_with_custom_data(self):
        """Test event with custom data payload."""
        event = TelemetryEvent(
            id=uuid4(),
            type="content_cited",
            timestamp=datetime.now(UTC),
            content_id=uuid4(),
            data={
                "citation_type": "direct_quote",
                "quote_length": 50,
                "position": "middle",
            },
        )
        assert event.data["citation_type"] == "direct_quote"


class TestSessionOutcome:
    """Tests for SessionOutcome model."""

    def test_conversion_outcome(self):
        """Test conversion outcome with value."""
        product_ids = [uuid4(), uuid4()]
        outcome = SessionOutcome(
            type="conversion",
            value_amount=9999,  # $99.99
            currency="USD",
            products=product_ids,
            metadata={"order_id": "ORD-123"},
        )
        assert outcome.type == "conversion"
        assert outcome.value_amount == 9999
        assert len(outcome.products) == 2

    def test_abandonment_outcome(self):
        """Test abandonment outcome."""
        outcome = SessionOutcome(
            type="abandonment",
            value_amount=4999,  # Cart value before abandonment
            currency="USD",
            metadata={"abandonment_step": "payment"},
        )
        assert outcome.type == "abandonment"

    def test_browse_outcome(self):
        """Test browse outcome (no conversion intent)."""
        outcome = SessionOutcome(
            type="browse",
        )
        assert outcome.type == "browse"
        assert outcome.value_amount == 0
        assert outcome.products == []

    def test_outcome_jpy_currency(self):
        """Test outcome with JPY currency."""
        outcome = SessionOutcome(
            type="conversion",
            value_amount=50000,  # ¥50,000
            currency="JPY",
        )
        assert outcome.value_amount == 50000
        assert outcome.currency == "JPY"

    def test_all_outcome_types(self):
        """Test all outcome types are valid."""
        outcome_types: list[OutcomeType] = ["conversion", "abandonment", "browse"]
        for outcome_type in outcome_types:
            outcome = SessionOutcome(type=outcome_type)
            assert outcome.type == outcome_type


class TestTelemetrySession:
    """Tests for TelemetrySession model."""

    def test_session_creation(self):
        """Test basic session creation."""
        session = TelemetrySession(
            session_id=uuid4(),
            mix_id="electronics-reviews",
            started_at=datetime.now(UTC),
        )
        assert session.schema_version == "0.1"
        assert session.mix_id == "electronics-reviews"
        assert session.events == []
        assert session.outcome is None

    def test_session_with_agent(self):
        """Test session with agent identifier."""
        session = TelemetrySession(
            session_id=uuid4(),
            agent_id="shopping-assistant-v2",
            mix_id="home-improvement",
            started_at=datetime.now(UTC),
        )
        assert session.agent_id == "shopping-assistant-v2"

    def test_session_with_user_context(self):
        """Test session with user context."""
        session = TelemetrySession(
            session_id=uuid4(),
            mix_id="test-mix",
            started_at=datetime.now(UTC),
            user_context=UserContext(
                external_id="user_abc",
                segments=["premium", "returning"],
            ),
        )
        assert session.user_context.external_id == "user_abc"
        assert "premium" in session.user_context.segments

    def test_complete_session_lifecycle(self):
        """Test complete session with events and outcome."""
        session_id = uuid4()
        content_id = uuid4()
        product_id = uuid4()

        session = TelemetrySession(
            session_id=session_id,
            agent_id="test-agent",
            mix_id="test-mix",
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            user_context=UserContext(segments=["test"]),
            events=[
                TelemetryEvent(
                    id=uuid4(),
                    type="turn_started",
                    timestamp=datetime.now(UTC),
                ),
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

        assert len(session.events) == 6
        assert session.outcome.type == "conversion"
        assert session.ended_at is not None


class TestSerialization:
    """Tests for JSON serialization."""

    def test_session_json_roundtrip(self):
        """Test TelemetrySession serializes and deserializes correctly."""
        session = TelemetrySession(
            session_id=uuid4(),
            mix_id="test",
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
        assert restored.mix_id == session.mix_id
        assert len(restored.events) == 1
        assert restored.outcome.type == "browse"

    def test_conversation_turn_json_roundtrip(self):
        """Test ConversationTurn serializes correctly."""
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
        """Test TelemetryEvent with turn serializes correctly."""
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
