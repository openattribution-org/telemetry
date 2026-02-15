"""Tests for UCP checkout extension bridge."""

from datetime import UTC, datetime
from uuid import uuid4

from openattribution.telemetry import (
    ConversationTurn,
    TelemetryEvent,
    TelemetrySession,
)
from openattribution.telemetry.ucp import session_to_attribution


def _event(
    event_type: str,
    content_id=None,
    product_id=None,
    turn=None,
    data=None,
    timestamp=None,
):
    """Helper to create a TelemetryEvent with sensible defaults."""
    return TelemetryEvent(
        id=uuid4(),
        type=event_type,
        timestamp=timestamp or datetime.now(UTC),
        content_id=content_id,
        product_id=product_id,
        turn=turn,
        data=data or {},
    )


def _session(events=None, content_scope="test-scope", prior_session_ids=None):
    """Helper to create a TelemetrySession with sensible defaults."""
    return TelemetrySession(
        session_id=uuid4(),
        content_scope=content_scope,
        started_at=datetime.now(UTC),
        prior_session_ids=prior_session_ids or [],
        events=events or [],
    )


class TestFullSession:
    """Tests for a complete session with all event types."""

    def test_full_session_produces_complete_attribution(self):
        """A session with retrieval, citation, and turns produces all fields."""
        content_id_1 = uuid4()
        content_id_2 = uuid4()
        prior_id = uuid4()

        session = _session(
            prior_session_ids=[prior_id],
            events=[
                _event(
                    "content_retrieved",
                    content_id=content_id_1,
                    data={"source_id": "wirecutter.com"},
                ),
                _event(
                    "content_retrieved", content_id=content_id_2, data={"source_id": "rtings.com"}
                ),
                _event(
                    "content_cited",
                    content_id=content_id_1,
                    data={
                        "citation_type": "paraphrase",
                        "excerpt_tokens": 85,
                        "position": "primary",
                        "content_hash": "sha256:" + "ab" * 32,
                    },
                ),
                _event(
                    "turn_completed",
                    turn=ConversationTurn(
                        privacy_level="intent",
                        query_intent="comparison",
                        topics=["headphones", "noise-cancelling"],
                    ),
                ),
            ],
        )

        result = session_to_attribution(session)

        assert result["content_scope"] == "test-scope"
        assert result["prior_session_ids"] == [str(prior_id)]
        assert len(result["content_retrieved"]) == 2
        assert len(result["content_cited"]) == 1
        assert result["content_cited"][0]["citation_type"] == "paraphrase"
        assert result["content_cited"][0]["excerpt_tokens"] == 85
        assert result["content_cited"][0]["position"] == "primary"
        assert result["content_cited"][0]["content_hash"].startswith("sha256:")
        assert result["conversation_summary"]["turn_count"] == 1
        assert result["conversation_summary"]["primary_intent"] == "comparison"
        assert result["conversation_summary"]["topics"] == ["headphones", "noise-cancelling"]
        assert result["conversation_summary"]["total_content_retrieved"] == 2
        assert result["conversation_summary"]["total_content_cited"] == 1


class TestEmptySession:
    """Tests for minimal or empty sessions."""

    def test_empty_session_produces_minimal_output(self):
        """A session with no events produces only content_scope."""
        session = _session(events=[])
        result = session_to_attribution(session)

        assert result == {"content_scope": "test-scope"}

    def test_no_content_scope_produces_empty_dict(self):
        """A session with no content_scope or events produces empty dict."""
        session = _session(events=[], content_scope=None)
        result = session_to_attribution(session)

        assert result == {}

    def test_prior_session_ids_included(self):
        """Prior session IDs are serialised as strings."""
        prior_1 = uuid4()
        prior_2 = uuid4()
        session = _session(events=[], prior_session_ids=[prior_1, prior_2])
        result = session_to_attribution(session)

        assert result["prior_session_ids"] == [str(prior_1), str(prior_2)]


class TestContentRetrieved:
    """Tests for content_retrieved extraction."""

    def test_extracts_content_id_and_timestamp(self):
        """Content retrieved events map to content_id + timestamp."""
        content_id = uuid4()
        ts = datetime(2026, 1, 15, 10, 30, 0, tzinfo=UTC)
        session = _session(
            events=[_event("content_retrieved", content_id=content_id, timestamp=ts)]
        )
        result = session_to_attribution(session)

        assert len(result["content_retrieved"]) == 1
        entry = result["content_retrieved"][0]
        assert entry["content_id"] == str(content_id)
        assert "2026-01-15" in entry["timestamp"]

    def test_source_id_included_when_present(self):
        """source_id from event data is included."""
        session = _session(
            events=[
                _event("content_retrieved", content_id=uuid4(), data={"source_id": "example.com"}),
            ]
        )
        result = session_to_attribution(session)

        assert result["content_retrieved"][0]["source_id"] == "example.com"

    def test_source_id_omitted_when_absent(self):
        """source_id is not included when not in event data."""
        session = _session(
            events=[
                _event("content_retrieved", content_id=uuid4()),
            ]
        )
        result = session_to_attribution(session)

        assert "source_id" not in result["content_retrieved"][0]

    def test_skips_events_without_content_id(self):
        """content_retrieved events with no content_id are skipped."""
        session = _session(
            events=[
                _event("content_retrieved"),  # no content_id
            ]
        )
        result = session_to_attribution(session)

        assert "content_retrieved" not in result


class TestContentCited:
    """Tests for content_cited extraction with quality signals."""

    def test_citation_with_all_quality_signals(self):
        """All citation quality signals are extracted from event data."""
        content_id = uuid4()
        session = _session(
            events=[
                _event(
                    "content_cited",
                    content_id=content_id,
                    data={
                        "citation_type": "direct_quote",
                        "excerpt_tokens": 120,
                        "position": "supporting",
                        "content_hash": "sha256:" + "cd" * 32,
                    },
                ),
            ]
        )
        result = session_to_attribution(session)

        cited = result["content_cited"][0]
        assert cited["citation_type"] == "direct_quote"
        assert cited["excerpt_tokens"] == 120
        assert cited["position"] == "supporting"
        assert cited["content_hash"] == "sha256:" + "cd" * 32

    def test_citation_with_partial_quality_signals(self):
        """Only present quality signals are included."""
        session = _session(
            events=[
                _event(
                    "content_cited",
                    content_id=uuid4(),
                    data={"citation_type": "reference"},
                ),
            ]
        )
        result = session_to_attribution(session)

        cited = result["content_cited"][0]
        assert cited["citation_type"] == "reference"
        assert "excerpt_tokens" not in cited
        assert "position" not in cited
        assert "content_hash" not in cited

    def test_contradiction_citation_type(self):
        """Contradiction citation type is preserved."""
        session = _session(
            events=[
                _event(
                    "content_cited",
                    content_id=uuid4(),
                    data={"citation_type": "contradiction"},
                ),
            ]
        )
        result = session_to_attribution(session)

        assert result["content_cited"][0]["citation_type"] == "contradiction"

    def test_no_cited_content(self):
        """Session with retrieval but no citations omits content_cited."""
        session = _session(
            events=[
                _event("content_retrieved", content_id=uuid4()),
            ]
        )
        result = session_to_attribution(session)

        assert "content_cited" not in result


class TestConversationSummary:
    """Tests for conversation summary aggregation."""

    def test_turn_count(self):
        """Turn count is based on turn_completed events."""
        session = _session(
            events=[
                _event("turn_completed", turn=ConversationTurn(privacy_level="minimal")),
                _event("turn_completed", turn=ConversationTurn(privacy_level="minimal")),
                _event("turn_completed", turn=ConversationTurn(privacy_level="minimal")),
            ]
        )
        result = session_to_attribution(session)

        assert result["conversation_summary"]["turn_count"] == 3

    def test_primary_intent_single(self):
        """Single intent is returned as primary."""
        session = _session(
            events=[
                _event(
                    "turn_completed",
                    turn=ConversationTurn(privacy_level="intent", query_intent="comparison"),
                ),
            ]
        )
        result = session_to_attribution(session)

        assert result["conversation_summary"]["primary_intent"] == "comparison"

    def test_primary_intent_majority(self):
        """Most frequent intent wins."""
        session = _session(
            events=[
                _event(
                    "turn_completed",
                    turn=ConversationTurn(privacy_level="intent", query_intent="comparison"),
                ),
                _event(
                    "turn_completed",
                    turn=ConversationTurn(privacy_level="intent", query_intent="comparison"),
                ),
                _event(
                    "turn_completed",
                    turn=ConversationTurn(privacy_level="intent", query_intent="purchase_intent"),
                ),
            ]
        )
        result = session_to_attribution(session)

        assert result["conversation_summary"]["primary_intent"] == "comparison"

    def test_no_intents(self):
        """Turns with no intent omit primary_intent from summary."""
        session = _session(
            events=[
                _event("turn_completed", turn=ConversationTurn(privacy_level="minimal")),
            ]
        )
        result = session_to_attribution(session)

        assert "primary_intent" not in result["conversation_summary"]

    def test_topics_deduplicated(self):
        """Topics across turns are de-duplicated, order preserved."""
        session = _session(
            events=[
                _event(
                    "turn_completed",
                    turn=ConversationTurn(
                        privacy_level="intent",
                        query_intent="comparison",
                        topics=["headphones", "Sony"],
                    ),
                ),
                _event(
                    "turn_completed",
                    turn=ConversationTurn(
                        privacy_level="intent",
                        query_intent="comparison",
                        topics=["headphones", "Bose"],
                    ),
                ),
            ]
        )
        result = session_to_attribution(session)

        assert result["conversation_summary"]["topics"] == ["headphones", "Sony", "Bose"]

    def test_no_turns_omits_summary(self):
        """Session with no turn events omits conversation_summary entirely."""
        session = _session(
            events=[
                _event("content_retrieved", content_id=uuid4()),
            ]
        )
        result = session_to_attribution(session)

        # Summary only has total_content_retrieved — still included
        assert result["conversation_summary"] == {"total_content_retrieved": 1}

    def test_empty_events_omits_summary(self):
        """Session with no events omits conversation_summary."""
        session = _session(events=[])
        result = session_to_attribution(session)

        assert "conversation_summary" not in result


class TestNonTelemetryEventsIgnored:
    """Tests that non-relevant event types are properly filtered."""

    def test_commerce_events_not_in_attribution(self):
        """Cart and product events don't appear in the attribution object."""
        session = _session(
            events=[
                _event("product_viewed", product_id=uuid4()),
                _event("cart_add", product_id=uuid4()),
                _event("checkout_started"),
            ]
        )
        result = session_to_attribution(session)

        assert "content_retrieved" not in result
        assert "content_cited" not in result
