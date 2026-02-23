"""Bridge from OpenAttribution telemetry sessions to UCP checkout attribution."""

from openattribution.telemetry._transforms import (
    _build_conversation_summary,
    _extract_content_cited,
    _extract_content_retrieved,
)
from openattribution.telemetry.schema import TelemetrySession


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
    summary = _build_conversation_summary(session)

    attribution: dict = {}

    if session.content_scope is not None:
        attribution["content_scope"] = session.content_scope

    if retrieved:
        attribution["content_retrieved"] = retrieved

    if cited:
        attribution["content_cited"] = cited

    if summary:
        attribution["conversation_summary"] = summary

    return attribution
