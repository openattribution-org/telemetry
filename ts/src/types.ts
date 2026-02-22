/**
 * OpenAttribution Telemetry — TypeScript types.
 *
 * Mirrors the Python schema (schema.py) exactly. JSON wire format uses
 * snake_case; these TypeScript types use camelCase with explicit mapping
 * in the client layer.
 *
 * Specification: https://openattribution.org/telemetry
 */

// ---------------------------------------------------------------------------
// Enumerations
// ---------------------------------------------------------------------------

/** Supported event types for telemetry tracking. */
export type EventType =
  // Content lifecycle
  | "content_retrieved"
  | "content_displayed"
  | "content_engaged"
  | "content_cited"
  // Conversation
  | "turn_started"
  | "turn_completed"
  // Commerce
  | "product_viewed"
  | "product_compared"
  | "cart_add"
  | "cart_remove"
  | "checkout_started"
  | "checkout_completed"
  | "checkout_abandoned";

/** Session outcome classifications. */
export type OutcomeType = "conversion" | "abandonment" | "browse";

/**
 * Privacy levels for conversation data sharing.
 * - `full`: Complete query and response text included.
 * - `summary`: LLM-generated summary of the conversation.
 * - `intent`: Only classified intent/topic, no raw text.
 * - `minimal`: Only metadata (token counts, content URLs).
 */
export type PrivacyLevel = "full" | "summary" | "intent" | "minimal";

/** Standardised intent categories for conversation classification. */
export type IntentCategory =
  | "product_research"
  | "comparison"
  | "how_to"
  | "troubleshooting"
  | "general_question"
  | "purchase_intent"
  | "price_check"
  | "availability_check"
  | "review_seeking"
  | "chitchat"
  | "other";

/** Actor type for the session initiator. */
export type InitiatorType = "user" | "agent";

/** How a cited piece of content was used in an agent response. */
export type CitationType =
  | "direct_quote"
  | "paraphrase"
  | "reference"
  | "contradiction";

/** Prominence of cited content within a response. */
export type CitationPosition = "primary" | "supporting" | "mentioned";

// ---------------------------------------------------------------------------
// Core models
// ---------------------------------------------------------------------------

/** Identity of the initiating agent (when initiator_type is "agent"). */
export interface Initiator {
  agentId?: string;
  manifestRef?: string;
  operatorId?: string;
}

/**
 * User context for segmentation and attribution.
 * Do not include PII — use hashed or synthetic identifiers.
 */
export interface UserContext {
  externalId?: string;
  segments?: string[];
  attributes?: Record<string, unknown>;
}

/**
 * Captured conversation turn with privacy controls.
 * Populate only the fields appropriate for your privacy level.
 */
export interface ConversationTurn {
  privacyLevel?: PrivacyLevel;
  // full / summary level
  queryText?: string;
  responseText?: string;
  // intent level
  queryIntent?: IntentCategory;
  responseType?: string;
  topics?: string[];
  // minimal level (always safe)
  contentUrlsRetrieved?: string[];
  contentUrlsCited?: string[];
  queryTokens?: number;
  responseTokens?: number;
  modelId?: string;
}

/** Single telemetry event within a session. */
export interface TelemetryEvent {
  /** Unique event identifier (UUID v4). */
  id: string;
  type: EventType;
  /** UTC timestamp in ISO 8601 format. */
  timestamp: string;
  /** Associated content URL, if applicable. */
  contentUrl?: string;
  /** Associated product UUID, if applicable. */
  productId?: string;
  /** Conversation turn data for turn_started/turn_completed events. */
  turn?: ConversationTurn;
  /** Additional event-specific metadata. */
  data?: Record<string, unknown>;
}

/** Session outcome for attribution calculation. */
export interface SessionOutcome {
  type: OutcomeType;
  /** Monetary value in minor currency units (e.g. 4999 = $49.99). */
  valueAmount?: number;
  /** ISO 4217 currency code. Default: "USD". */
  currency?: string;
  /** Product UUIDs involved in the outcome. */
  products?: string[];
  metadata?: Record<string, unknown>;
}

/** Options for starting a new session. */
export interface StartSessionOptions {
  contentScope?: string;
  agentId?: string;
  externalSessionId?: string;
  userContext?: UserContext;
  manifestRef?: string;
  priorSessionIds?: string[];
  initiatorType?: InitiatorType;
  initiator?: Initiator;
}

/** Complete telemetry session (for bulk upload). */
export interface TelemetrySession {
  schemaVersion?: string;
  sessionId: string;
  initiatorType?: InitiatorType;
  initiator?: Initiator;
  agentId?: string;
  contentScope?: string;
  manifestRef?: string;
  priorSessionIds?: string[];
  startedAt: string;
  endedAt?: string;
  userContext?: UserContext;
  events: TelemetryEvent[];
  outcome?: SessionOutcome;
}

/** Options for TelemetryClient. */
export interface TelemetryClientOptions {
  /** Base URL of the OpenAttribution Telemetry server. */
  endpoint: string;
  /** API key sent as X-API-Key header. */
  apiKey?: string;
  /**
   * If true, failed requests are logged and swallowed rather than thrown.
   * Default: true.
   */
  failSilently?: boolean;
  /** Request timeout in milliseconds. Default: 30_000. */
  timeout?: number;
  /** Maximum retry attempts for transient errors. Default: 3. */
  maxRetries?: number;
}
