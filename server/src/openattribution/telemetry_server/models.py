"""Server-side models for OpenAttribution Telemetry."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# Re-export SDK schema types for convenience
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
    # SDK re-exports
    "ConversationTurn",
    "EventType",
    "IntentCategory",
    "OutcomeType",
    "PrivacyLevel",
    "SessionOutcome",
    "TelemetryEvent",
    "TelemetrySession",
    "UserContext",
    # Server models
    "SessionCreate",
    "SessionEnd",
    "EventsCreate",
    "Session",
    "Event",
    "SessionWithEvents",
    "SessionSummary",
]


# =============================================================================
# API Input Models
# =============================================================================


class SessionCreate(BaseModel):
    """Input for POST /session/start (matches SDK client)."""

    content_scope: str | None = None
    manifest_ref: str | None = None
    agent_id: str | None = None
    external_session_id: str | None = None
    user_context: dict = Field(default_factory=dict)
    prior_session_ids: list[str] = Field(default_factory=list)


class SessionEnd(BaseModel):
    """Input for POST /session/end."""

    session_id: str
    outcome: SessionOutcome


class EventsCreate(BaseModel):
    """Input for POST /events."""

    session_id: str
    events: list[TelemetryEvent]


# =============================================================================
# Database Models
# =============================================================================


class Session(BaseModel):
    """Full session from database."""

    id: UUID
    content_scope: str | None
    manifest_ref: str | None
    config_snapshot_hash: str | None
    agent_id: str | None
    external_session_id: str | None
    prior_session_ids: list[UUID]
    user_context: dict
    started_at: datetime
    ended_at: datetime | None
    outcome_type: str | None
    outcome_value: dict | None
    created_at: datetime
    updated_at: datetime


class Event(BaseModel):
    """Full event from database."""

    id: UUID
    session_id: UUID
    event_type: str
    content_id: UUID | None
    product_id: UUID | None
    turn_data: dict | None
    event_data: dict
    event_timestamp: datetime
    created_at: datetime


class SessionWithEvents(Session):
    """Session with all events (for attribution systems)."""

    events: list[Event] = Field(default_factory=list)


class SessionSummary(BaseModel):
    """Lightweight session for list queries."""

    id: UUID
    content_scope: str | None
    external_session_id: str | None
    outcome_type: str | None
    started_at: datetime
    ended_at: datetime | None
