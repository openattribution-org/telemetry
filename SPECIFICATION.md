# OpenAttribution Specification

**Version:** 0.2
**Status:** Preview
**Last Updated:** 2026-01

## Abstract

OpenAttribution is an open standard for tracking content attribution in AI agent interactions. It enables content creators to receive fair compensation when their content contributes to AI-generated responses that drive user outcomes.

## 1. Introduction

### 1.1 Problem Statement

AI agents increasingly use licensed content to generate helpful responses. However, there is no standardized way to:

1. Track which content was retrieved and used in a response
2. Attribute user outcomes (purchases, signups) to specific content
3. Enable fair compensation for content creators based on contribution

### 1.2 Goals

OpenAttribution aims to:

- Define a **minimal, extensible schema** for telemetry events
- Support **privacy-preserving** data sharing between parties
- Enable **attribution calculation** across the content lifecycle
- Remain **vendor-neutral** and open source

### 1.3 Non-Goals

OpenAttribution does not:

- Define specific attribution algorithms (left to implementers)
- Mandate specific privacy policies (left to agreements between parties)
- Require specific transport protocols (HTTP, gRPC, etc. all valid)

## 2. Concepts

### 2.1 Actors

| Actor | Description |
|-------|-------------|
| **Content Owner** | Entity that owns/licenses content (publishers, creators) |
| **Agent Operator** | Entity running the AI agent that uses content |
| **Attribution Consumer** | Entity that processes telemetry for attribution (may be same as owner) |
| **End User** | Human interacting with the AI agent |

### 2.2 Session Model

A **Session** represents a bounded interaction between an end user and an AI agent. Sessions:

- Have a unique identifier
- Track the content collection (ContentMix) used
- Contain ordered **Events**
- Conclude with an optional **Outcome**

```
Session
├── started_at
├── events[]
│   ├── content_retrieved
│   ├── turn_started
│   ├── content_cited
│   ├── turn_completed
│   └── ...
├── ended_at
└── outcome (conversion/abandonment/browse)
```

### 2.3 Event Lifecycle

Content flows through these stages during an agent interaction:

1. **Retrieved**: Content fetched from storage/index
2. **Displayed**: Content shown to user (if applicable)
3. **Cited**: Content used/quoted in agent response
4. **Engaged**: User interacted with content (clicked, expanded)

Conversation turns overlay this lifecycle:

1. **Turn Started**: User submits a query
2. **Turn Completed**: Agent finishes response

## 3. Schema

### 3.1 Session

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | Yes | Schema version (e.g., "0.2") |
| `session_id` | UUID | Yes | Unique session identifier |
| `agent_id` | string | No | Agent identifier (for multi-agent systems) |
| `content_scope` | string | No | Opaque content collection identifier (see 3.1.1) |
| `manifest_ref` | string | No | AIMS manifest reference (see 3.1.2) |
| `prior_session_ids` | UUID[] | No | Previous sessions in journey (see 3.1.3) |
| `started_at` | datetime | Yes | Session start (UTC) |
| `ended_at` | datetime | No | Session end (UTC) |
| `user_context` | UserContext | No | User segmentation data |
| `events` | Event[] | No | Ordered list of events |
| `outcome` | SessionOutcome | No | Final session outcome |

#### 3.1.1 Content Scope

The `content_scope` field is an opaque identifier that groups sessions by their content access context. Implementers define its meaning based on their architecture:

| Implementation | `content_scope` Value |
|----------------|----------------------|
| Content mix platform | Mix ID (e.g., "electronics-reviews") |
| AIMS-based system | Manifest DID (e.g., "did:aims:abc123") |
| API key scoped | API key identifier |
| Customer agreement | Agreement or contract ID |

This field enables attribution aggregation across sessions using the same content collection without mandating a specific access control model.

#### 3.1.2 Manifest Reference

The `manifest_ref` field optionally references an [AIMS (AI Manifest Standard)](https://github.com/openattribution-org/aims) manifest. This enables:

- Verification that cited content was licensed at session time
- Cross-referencing telemetry with licensing agreements
- Audit trails for content usage compliance

Format: AIMS DID (e.g., `did:aims:abc123`) or URL to manifest.

#### 3.1.3 Cross-Session Attribution

The `prior_session_ids` field enables attribution across multi-session user journeys:

```
Day 1: Research session (Session A)
Day 3: Comparison session (Session B, prior_session_ids: [A])
Day 7: Purchase session (Session C, prior_session_ids: [A, B])
```

This supports:
- Multi-day customer journeys (common in high-consideration purchases)
- Cross-device attribution (user researches on mobile, converts on desktop)
- Returning visitor attribution

Attribution algorithms can use this chain to distribute credit across the full journey rather than just the converting session.

### 3.2 Event

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Unique event identifier |
| `type` | EventType | Yes | Event type (see 3.3) |
| `timestamp` | datetime | Yes | Event timestamp (UTC) |
| `content_id` | UUID | No | Associated content document |
| `product_id` | UUID | No | Associated product |
| `turn` | ConversationTurn | No | Conversation data (for turn events) |
| `data` | object | No | Additional event metadata |

### 3.3 Event Types

#### Content Events

| Type | Description | Expected Fields |
|------|-------------|-----------------|
| `content_retrieved` | Content fetched from source | `content_id` |
| `content_displayed` | Content shown to user | `content_id` |
| `content_engaged` | User interacted with content | `content_id`, `data.engagement_type` |
| `content_cited` | Content referenced in response | `content_id`, `data.*` (see below) |

##### Citation Quality Signals

The `content_cited` event supports optional quality signals in the `data` field to enable more accurate attribution:

| Field | Type | Description |
|-------|------|-------------|
| `data.citation_type` | string | How content was used: `direct_quote`, `paraphrase`, `reference`, `contradiction` |
| `data.excerpt_tokens` | integer | Token count of the excerpt used |
| `data.position` | string | Prominence in response: `primary`, `supporting`, `mentioned` |
| `data.content_hash` | string | SHA256 of cited content (for verification) |

**Citation Types:**

- `direct_quote`: Verbatim or near-verbatim reproduction
- `paraphrase`: Restated in different words
- `reference`: Mentioned or linked without quoting
- `contradiction`: Content was retrieved but contradicted/corrected

The `contradiction` type enables negative attribution—content that was retrieved but explicitly disagreed with should not receive positive credit.

**Example:**

```json
{
  "type": "content_cited",
  "content_id": "770e8400-e29b-41d4-a716-446655440010",
  "data": {
    "citation_type": "paraphrase",
    "excerpt_tokens": 85,
    "position": "primary",
    "content_hash": "sha256:a1b2c3..."
  }
}
```

#### Conversation Events

| Type | Description | Expected Fields |
|------|-------------|-----------------|
| `turn_started` | User initiated a turn | `turn` |
| `turn_completed` | Agent finished responding | `turn` |

#### Commerce Events

| Type | Description | Expected Fields |
|------|-------------|-----------------|
| `product_viewed` | Product page viewed | `product_id` |
| `product_compared` | Products compared | `data.product_ids` |
| `cart_add` | Item added to cart | `product_id` |
| `cart_remove` | Item removed from cart | `product_id` |
| `checkout_started` | Checkout initiated | `data.cart_value_amount`, `data.currency` |
| `checkout_completed` | Purchase completed | `data.order_value_amount`, `data.currency` |
| `checkout_abandoned` | Checkout abandoned | - |

### 3.4 Conversation Turn

The `ConversationTurn` object captures query/response data with privacy controls.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `privacy_level` | PrivacyLevel | Yes | Data sharing level |
| `query_text` | string | No | User's query (full/summary) |
| `response_text` | string | No | Agent's response (full/summary) |
| `query_intent` | IntentCategory | No | Classified intent (intent+) |
| `response_type` | string | No | Response classification |
| `topics` | string[] | No | Detected topics/entities |
| `content_ids_retrieved` | UUID[] | No | Content fetched |
| `content_ids_cited` | UUID[] | No | Content used in response |
| `query_tokens` | integer | No | Query token count |
| `response_tokens` | integer | No | Response token count |
| `model_id` | string | No | Model identifier |

### 3.5 Privacy Levels

| Level | Query/Response Text | Intent | Topics | Token Counts | Content IDs |
|-------|---------------------|--------|--------|--------------|-------------|
| `full` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `summary` | ✓ (summarized) | ✓ | ✓ | ✓ | ✓ |
| `intent` | ✗ | ✓ | ✓ | ✓ | ✓ |
| `minimal` | ✗ | ✗ | ✗ | ✓ | ✓ |

### 3.6 Intent Categories

Standardized intent classifications:

**Research Intents:**
- `product_research` - Researching products/services
- `comparison` - Comparing options
- `how_to` - Seeking instructions
- `troubleshooting` - Solving a problem
- `general_question` - General information seeking

**Commerce Intents:**
- `purchase_intent` - Ready to buy
- `price_check` - Checking prices
- `availability_check` - Checking availability
- `review_seeking` - Looking for reviews

**Other:**
- `chitchat` - Social conversation
- `other` - Uncategorized

### 3.7 Session Outcome

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | OutcomeType | Yes | conversion/abandonment/browse |
| `value_amount` | integer | No | Monetary value in minor currency units |
| `currency` | string | No | ISO 4217 currency code |
| `products` | UUID[] | No | Products in outcome |
| `metadata` | object | No | Additional outcome data |

**Minor Currency Units:**

Monetary values are stored as integers in the smallest denomination of the currency:
- USD/EUR: cents (e.g., $49.99 = 4999)
- GBP: pence (e.g., £49.99 = 4999)
- JPY: yen (e.g., ¥5000 = 5000, no subdivision)
- KWD: fils (e.g., 1.000 KWD = 1000, 3 decimal places)

This follows the standard pattern used by Stripe and other payment processors.

### 3.8 User Context

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `external_id` | string | No | Opaque user identifier (not PII) |
| `segments` | string[] | No | User segment labels |
| `attributes` | object | No | Additional attributes |

## 4. Transport

OpenAttribution is transport-agnostic. Implementations may use:

- HTTP/REST (recommended for simplicity)
- gRPC (for high-throughput scenarios)
- Message queues (for async processing)
- Direct database writes (for co-located systems)

### 4.1 Recommended HTTP Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/session/start` | POST | Start a new session |
| `/events` | POST | Record events (batch) |
| `/session/end` | POST | End session with outcome |

### 4.2 Authentication

Implementations SHOULD use API keys or OAuth tokens. The standard does not mandate a specific authentication mechanism.

## 5. Privacy Considerations

### 5.1 Data Minimization

Emitters SHOULD:

- Use the minimum `privacy_level` necessary for their use case
- Avoid including PII in `user_context.external_id`
- Hash or anonymize identifiers where possible

### 5.2 Data Agreements

The appropriate privacy level depends on the trust relationship between parties. Common scenarios:

| Scenario | Recommended Level |
|----------|-------------------|
| First-party analytics | `full` |
| Trusted partner | `summary` or `intent` |
| Third-party attribution | `intent` or `minimal` |
| Public benchmarking | `minimal` |

### 5.3 Retention

This specification does not mandate retention periods. Consumers SHOULD document their retention policies.

## 6. Attribution

OpenAttribution provides the telemetry data needed for attribution but does not mandate specific algorithms. Common approaches include:

- **Last-touch**: Credit to last content before conversion
- **First-touch**: Credit to first content in session
- **Linear**: Equal credit to all content
- **Position-based**: Weighted by position in journey
- **SHAP-based**: Game-theoretic contribution scores

## 7. Extensibility

### 7.1 Custom Event Types

Implementations MAY define custom event types using the `data` field:

```json
{
  "type": "content_engaged",
  "data": {
    "custom_event_subtype": "video_watched",
    "watch_duration_seconds": 45
  }
}
```

### 7.2 Custom Intent Categories

For intents not covered by the standard categories, use `other` and include details in `topics`:

```json
{
  "query_intent": "other",
  "topics": ["legal_advice", "contract_review"]
}
```

## 8. Versioning

Schema versions follow semantic versioning principles:

- **Major** (1.0 → 2.0): Breaking changes to required fields
- **Minor** (0.1 → 0.1): New optional fields, new event types
- **Patch** (0.1.0 → 0.1.1): Clarifications, typo fixes

Consumers SHOULD accept sessions with compatible minor versions.

## Appendix A: JSON Schema

See `schema.json` in the repository for the formal JSON Schema definition.

## Appendix B: Example Session

```json
{
  "schema_version": "0.2",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_id": "shopping-assistant-v2",
  "content_scope": "electronics-reviews",
  "manifest_ref": "did:aims:retailer-content-2026",
  "prior_session_ids": ["440e8400-e29b-41d4-a716-446655440999"],
  "started_at": "2026-01-15T10:30:00Z",
  "ended_at": "2026-01-15T10:35:00Z",
  "user_context": {
    "external_id": "user_abc123_hash",
    "segments": ["returning", "premium"],
    "attributes": {}
  },
  "events": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "type": "turn_started",
      "timestamp": "2026-01-15T10:30:00Z",
      "turn": {
        "privacy_level": "intent",
        "query_intent": "comparison",
        "topics": ["headphones", "noise-cancelling"],
        "query_tokens": 15
      }
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440002",
      "type": "content_retrieved",
      "timestamp": "2026-01-15T10:30:01Z",
      "content_id": "770e8400-e29b-41d4-a716-446655440010"
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440003",
      "type": "content_retrieved",
      "timestamp": "2026-01-15T10:30:01Z",
      "content_id": "770e8400-e29b-41d4-a716-446655440011"
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440004",
      "type": "content_cited",
      "timestamp": "2026-01-15T10:30:05Z",
      "content_id": "770e8400-e29b-41d4-a716-446655440010",
      "data": {
        "citation_type": "paraphrase",
        "excerpt_tokens": 85,
        "position": "primary"
      }
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440005",
      "type": "turn_completed",
      "timestamp": "2026-01-15T10:30:05Z",
      "turn": {
        "privacy_level": "intent",
        "query_intent": "comparison",
        "response_type": "recommendation",
        "topics": ["headphones", "Sony WH-1000XM5", "Bose QC45"],
        "content_ids_retrieved": [
          "770e8400-e29b-41d4-a716-446655440010",
          "770e8400-e29b-41d4-a716-446655440011"
        ],
        "content_ids_cited": [
          "770e8400-e29b-41d4-a716-446655440010"
        ],
        "response_tokens": 150,
        "model_id": "claude-3-opus"
      }
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440006",
      "type": "product_viewed",
      "timestamp": "2026-01-15T10:32:00Z",
      "product_id": "880e8400-e29b-41d4-a716-446655440020"
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440007",
      "type": "cart_add",
      "timestamp": "2026-01-15T10:34:00Z",
      "product_id": "880e8400-e29b-41d4-a716-446655440020"
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440008",
      "type": "checkout_completed",
      "timestamp": "2026-01-15T10:35:00Z",
      "data": {"order_value_amount": 34999, "currency": "USD"}
    }
  ],
  "outcome": {
    "type": "conversion",
    "value_amount": 34999,
    "currency": "USD",
    "products": ["880e8400-e29b-41d4-a716-446655440020"]
  }
}
```

## Appendix C: Changelog

### v0.2 (2026-01)

Cross-session attribution and content scope abstraction.

- **Breaking:** Renamed `mix_id` to `content_scope` (now optional)
- Added `manifest_ref` for AIMS integration
- Added `prior_session_ids` for cross-session journey attribution
- Added citation quality signals (`citation_type`, `excerpt_tokens`, `position`, `content_hash`)
- Added `contradiction` citation type for negative attribution
- Documentation for content scope patterns and AIMS integration

### v0.1 (2026-01)

Initial preview release.

- Core session and event model
- Content lifecycle events (retrieved, displayed, engaged, cited)
- Conversation events (`turn_started`, `turn_completed`)
- Commerce events (cart, checkout)
- `ConversationTurn` model with privacy levels
- `IntentCategory` for standardized intent classification
- `SessionOutcome` for attribution calculation
