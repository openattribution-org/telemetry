"""
OpenAttribution Telemetry - SDK for AI content attribution.

OpenAttribution enables fair compensation for content creators when their
content is used by AI agents to generate valuable responses.

Example:
    >>> from openattribution.telemetry import Client, ConversationTurn
    >>> async with Client(endpoint, api_key) as client:
    ...     session_id = await client.start_session(mix_id="my-mix")
    ...     await client.record_event(
    ...         session_id=session_id,
    ...         event_type="turn_completed",
    ...         turn=ConversationTurn(privacy_level="intent", query_intent="comparison")
    ...     )
"""

from openattribution.telemetry.client import Client
from openattribution.telemetry.schema import (
    ConversationTurn,
    EventType,
    IntentCategory,
    OutcomeType,
    PrivacyLevel,
    SessionOutcome,
    TelemetryEvent,
    TelemetrySession,
    UserContext,
)

__all__ = [
    # Client
    "Client",
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
