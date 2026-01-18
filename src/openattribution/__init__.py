"""
OpenAttribution - Open standard and SDK for AI content attribution.

OpenAttribution enables fair compensation for content creators when their
content is used by AI agents to generate valuable responses.

Example:
    >>> from openattribution import OpenAttributionClient, ConversationTurn
    >>> async with OpenAttributionClient(endpoint, api_key) as client:
    ...     session_id = await client.start_session(mix_id="my-mix")
    ...     await client.record_event(
    ...         session_id=session_id,
    ...         event_type="turn_completed",
    ...         turn=ConversationTurn(privacy_level="intent", query_intent="comparison")
    ...     )
"""

from openattribution.client import OpenAttributionClient
from openattribution.schema import (
    ConversationTurn,
    # Type aliases
    EventType,
    IntentCategory,
    OutcomeType,
    PrivacyLevel,
    SessionOutcome,
    TelemetryEvent,
    TelemetrySession,
    # Models
    UserContext,
)

__all__ = [
    # Client
    "OpenAttributionClient",
    # Type aliases
    "EventType",
    "OutcomeType",
    "PrivacyLevel",
    "IntentCategory",
    # Models
    "UserContext",
    "ConversationTurn",
    "TelemetryEvent",
    "SessionOutcome",
    "TelemetrySession",
]

__version__ = "0.1.0"
