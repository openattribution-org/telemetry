"""Bridge from OpenAttribution telemetry sessions to UCP checkout attribution."""

from collections import Counter

from openattribution.telemetry.schema import TelemetrySession

_CITATION_DATA_FIELDS = ("citation_type", "excerpt_tokens", "position", "content_hash")


def session_to_attribution(session: TelemetrySession) -> dict:
    """Convert a TelemetrySession into a UCP checkout ``attribution`` object.

    The returned dict matches the schema defined in
    ``ucp/extension-schema.json`` and can be embedded directly in a
    UCP checkout session payload.

    Args:
        session: A complete or in-progress telemetry session.

    Returns:
        A dict containing the ``attribution`` object fields.
    """
    retrieved = _extract_content_retrieved(session)
    cited = _extract_content_cited(session)
    summary = _build_conversation_summary(session, len(retrieved), len(cited))

    attribution: dict = {}

    if session.content_scope is not None:
        attribution["content_scope"] = session.content_scope

    if session.prior_session_ids:
        attribution["prior_session_ids"] = [str(sid) for sid in session.prior_session_ids]

    if retrieved:
        attribution["content_retrieved"] = retrieved

    if cited:
        attribution["content_cited"] = cited

    if summary:
        attribution["conversation_summary"] = summary

    return attribution


def _extract_content_retrieved(session: TelemetrySession) -> list[dict]:
    """Extract content_retrieved entries from session events."""
    results = []
    for event in session.events:
        if event.type != "content_retrieved" or event.content_id is None:
            continue
        entry: dict = {
            "content_id": str(event.content_id),
            "timestamp": event.timestamp.isoformat(),
        }
        source_id = event.data.get("source_id")
        if source_id is not None:
            entry["source_id"] = source_id
        results.append(entry)
    return results


def _extract_content_cited(session: TelemetrySession) -> list[dict]:
    """Extract content_cited entries with quality signals from session events."""
    results = []
    for event in session.events:
        if event.type != "content_cited" or event.content_id is None:
            continue
        entry: dict = {
            "content_id": str(event.content_id),
            "timestamp": event.timestamp.isoformat(),
        }
        for field in _CITATION_DATA_FIELDS:
            value = event.data.get(field)
            if value is not None:
                entry[field] = value
        results.append(entry)
    return results


def _build_conversation_summary(
    session: TelemetrySession,
    total_retrieved: int,
    total_cited: int,
) -> dict:
    """Build a privacy-preserving conversation summary from turn events."""
    intents: list[str] = []
    topics_seen: dict[str, None] = {}  # ordered set
    turn_count = 0

    for event in session.events:
        if event.type != "turn_completed":
            continue
        turn_count += 1
        if event.turn is not None:
            if event.turn.query_intent is not None:
                intents.append(event.turn.query_intent)
            for topic in event.turn.topics:
                topics_seen[topic] = None

    summary: dict = {}

    if turn_count > 0:
        summary["turn_count"] = turn_count

    if intents:
        counter = Counter(intents)
        summary["primary_intent"] = counter.most_common(1)[0][0]

    topics = list(topics_seen)
    if topics:
        summary["topics"] = topics

    if total_retrieved > 0:
        summary["total_content_retrieved"] = total_retrieved

    if total_cited > 0:
        summary["total_content_cited"] = total_cited

    return summary
