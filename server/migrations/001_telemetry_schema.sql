-- OpenAttribution Telemetry Server Schema
-- Reference implementation for the OpenAttribution Telemetry standard
-- https://github.com/openattribution-org/telemetry

-- Helper function for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Sessions table
-- Represents a bounded interaction between an end user and an AI agent
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Content scope: opaque identifier for the content collection/permissions context
    -- Implementers define the meaning (e.g., mix ID, manifest reference, API key scope)
    content_scope TEXT,

    -- AIMS manifest reference for licensing verification (e.g., "did:aims:abc123")
    manifest_ref TEXT,

    -- Fraud prevention: hash of content configuration at session start
    config_snapshot_hash TEXT,

    -- Agent identifier (for multi-agent systems)
    agent_id TEXT,

    -- External session ID for lookups (your system's session/user ID)
    external_session_id TEXT,

    -- Cross-session journey linking: previous session IDs in the same user journey
    -- Enables multi-day or multi-device attribution
    prior_session_ids UUID[] DEFAULT '{}',

    -- User context for segmentation (no PII - use hashed/synthetic IDs)
    user_context JSONB NOT NULL DEFAULT '{}',

    -- Session lifecycle
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,

    -- Session outcome
    outcome_type TEXT,
    outcome_value JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Outcome type must be one of the standard types
    CONSTRAINT sessions_outcome_type_check CHECK (
        outcome_type IS NULL OR outcome_type IN ('conversion', 'abandonment', 'browse')
    )
);

-- Events table
-- Individual telemetry events within a session
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Event type (standard OpenAttribution event types)
    event_type TEXT NOT NULL,

    -- Content reference
    content_id UUID,

    -- Product reference (for commerce events)
    product_id UUID,

    -- Conversation turn data (for turn_started/turn_completed events)
    -- Contains privacy-controlled conversation information
    turn_data JSONB,

    -- Additional event metadata
    -- For content_cited events, may include: citation_type, excerpt_tokens, position, content_hash
    event_data JSONB NOT NULL DEFAULT '{}',

    -- When the event occurred
    event_timestamp TIMESTAMPTZ NOT NULL,

    -- When the record was created
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Event type must be one of the standard types
    CONSTRAINT events_type_check CHECK (
        event_type IN (
            -- Content lifecycle events
            'content_retrieved', 'content_displayed', 'content_engaged', 'content_cited',
            -- Conversation events
            'turn_started', 'turn_completed',
            -- Commerce events
            'product_viewed', 'product_compared', 'cart_add', 'cart_remove',
            'checkout_started', 'checkout_completed', 'checkout_abandoned'
        )
    )
);

-- Indexes for common query patterns

-- Filter sessions by content scope
CREATE INDEX idx_sessions_scope ON sessions(content_scope) WHERE content_scope IS NOT NULL;

-- Look up sessions by external ID (your system's session ID)
CREATE INDEX idx_sessions_external ON sessions(external_session_id) WHERE external_session_id IS NOT NULL;

-- Filter sessions by outcome type (for attribution processing)
CREATE INDEX idx_sessions_outcome ON sessions(outcome_type) WHERE outcome_type IS NOT NULL;

-- Filter sessions by end time (for batch processing time ranges)
CREATE INDEX idx_sessions_ended ON sessions(ended_at) WHERE ended_at IS NOT NULL;

-- Look up events by session, ordered by time
CREATE INDEX idx_events_session ON events(session_id, event_timestamp);

-- Find events by content ID (for content-level attribution)
CREATE INDEX idx_events_content ON events(content_id) WHERE content_id IS NOT NULL;

-- GIN index for "find sessions that followed session X" queries
-- Useful for journey reconstruction
CREATE INDEX idx_sessions_prior ON sessions USING GIN (prior_session_ids);

-- Auto-update updated_at timestamp
CREATE TRIGGER sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
