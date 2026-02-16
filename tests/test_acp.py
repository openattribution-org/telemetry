"""Tests for ACP content attribution bridge."""

from datetime import UTC, datetime
from uuid import uuid4

from openattribution.telemetry import (
    ConversationTurn,
    TelemetryEvent,
    TelemetrySession,
)
from openattribution.telemetry.acp import session_to_content_attribution


def _event(
    event_type: str,
    content_url=None,
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
        content_url=content_url,
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
    """Test that a complete session produces a full content_attribution object."""

    def test_full_session_produces_complete_content_attribution(self):
        """A session with retrieval, citation, and turns produces all fields."""
        url_1 = "https://www.jameshoffmann.co.uk/reviews/breville-barista-express"
        url_2 = "https://www.home-barista.com/espresso-machines/review.html"
        prior_id = uuid4()

        session = _session(
            prior_session_ids=[prior_id],
            events=[
                _event("content_retrieved", content_url=url_1),
                _event("content_retrieved", content_url=url_2),
                _event(
                    "content_cited",
                    content_url=url_1,
                    data={
                        "citation_type": "paraphrase",
                        "excerpt_tokens": 95,
                        "position": "primary",
                        "content_hash": "sha256:" + "ab" * 32,
                    },
                ),
                _event(
                    "turn_completed",
                    turn=ConversationTurn(
                        privacy_level="intent",
                        query_intent="comparison",
                        topics=["espresso-machine", "grinder"],
                    ),
                ),
            ],
        )

        result = session_to_content_attribution(session)

        assert result["content_scope"] == "test-scope"
        assert result["prior_session_ids"] == [str(prior_id)]
        assert len(result["content_retrieved"]) == 2
        assert len(result["content_cited"]) == 1
        assert result["content_cited"][0]["citation_type"] == "paraphrase"
        assert result["content_cited"][0]["excerpt_tokens"] == 95
        assert result["conversation_summary"]["turn_count"] == 1
        assert result["conversation_summary"]["primary_intent"] == "comparison"
        assert result["conversation_summary"]["topics"] == ["espresso-machine", "grinder"]
        assert result["conversation_summary"]["total_content_retrieved"] == 2
        assert result["conversation_summary"]["total_content_cited"] == 1


class TestEmptySession:
    """Test minimal and empty sessions."""

    def test_empty_session_produces_minimal_output(self):
        """A session with no events produces only content_scope."""
        session = _session(events=[])
        result = session_to_content_attribution(session)

        assert result == {"content_scope": "test-scope"}

    def test_no_content_scope_produces_empty_dict(self):
        """A session with no content_scope or events produces empty dict."""
        session = _session(events=[], content_scope=None)
        result = session_to_content_attribution(session)

        assert result == {}


class TestContentCited:
    """Test content_cited extraction with quality signals."""

    def test_citation_with_all_quality_signals(self):
        """All citation quality signals are extracted from event data."""
        session = _session(
            events=[
                _event(
                    "content_cited",
                    content_url="https://example.com/review",
                    data={
                        "citation_type": "direct_quote",
                        "excerpt_tokens": 120,
                        "position": "supporting",
                        "content_hash": "sha256:" + "cd" * 32,
                    },
                ),
            ]
        )
        result = session_to_content_attribution(session)

        cited = result["content_cited"][0]
        assert cited["citation_type"] == "direct_quote"
        assert cited["excerpt_tokens"] == 120
        assert cited["position"] == "supporting"
        assert cited["content_hash"] == "sha256:" + "cd" * 32


class TestConversationSummary:
    """Test conversation summary aggregation."""

    def test_summary_with_multiple_turns(self):
        """Summary aggregates across multiple turn events."""
        session = _session(
            events=[
                _event(
                    "content_retrieved",
                    content_url="https://example.com/article",
                ),
                _event(
                    "turn_completed",
                    turn=ConversationTurn(
                        privacy_level="intent",
                        query_intent="comparison",
                        topics=["espresso-machine", "grinder"],
                    ),
                ),
                _event(
                    "turn_completed",
                    turn=ConversationTurn(
                        privacy_level="intent",
                        query_intent="purchase_intent",
                        topics=["espresso-machine", "price"],
                    ),
                ),
            ]
        )
        result = session_to_content_attribution(session)

        summary = result["conversation_summary"]
        assert summary["turn_count"] == 2
        assert summary["topics"] == ["espresso-machine", "grinder", "price"]
        assert summary["total_content_retrieved"] == 1


class TestNonTelemetryEventsIgnored:
    """Test that non-relevant event types are filtered out."""

    def test_commerce_events_not_in_content_attribution(self):
        """Cart and product events don't appear in the content_attribution object."""
        session = _session(
            events=[
                _event("product_viewed", product_id=uuid4()),
                _event("cart_add", product_id=uuid4()),
                _event("checkout_started"),
            ]
        )
        result = session_to_content_attribution(session)

        assert "content_retrieved" not in result
        assert "content_cited" not in result
