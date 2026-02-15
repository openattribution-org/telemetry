# OpenAttribution Telemetry Extension for UCP

**Extension Name:** `org.openattribution.telemetry`
**Version:** `2026-02-11`
**Extends:** `dev.ucp.shopping.checkout`
**Status:** Draft

## Overview

This extension augments UCP checkout sessions with content attribution telemetry. When an AI agent helps a user make a purchase, this extension tracks which content influenced the decision — enabling fair compensation for content creators whose work drove the sale.

## Why This Exists

AI commerce is opaque. When a shopping agent recommends a product, the recommendation is informed by reviews, guides, comparisons, and other content. Currently:

- Content creators have no visibility into whether their work influenced purchases
- Merchants can't measure which content partnerships drive ROI
- Attribution algorithms have no standardised signal to work with

This extension provides the telemetry layer. Attribution algorithms, payment structures, and business agreements remain outside scope.

## Capability Declaration

Merchants and agents declare support in their UCP profile:

```json
{
  "ucp": {
    "capabilities": [
      {
        "name": "dev.ucp.shopping.checkout",
        "version": "2026-01-11"
      },
      {
        "name": "org.openattribution.telemetry",
        "version": "2026-02-11",
        "spec": "https://openattribution.org/ucp/telemetry",
        "schema": "https://openattribution.org/ucp/schemas/extension.json",
        "extends": "dev.ucp.shopping.checkout"
      }
    ]
  }
}
```

## Schema

The extension adds an `attribution` object to checkout sessions:

```json
{
  "id": "chk_123456789",
  "status": "ready_for_complete",
  "line_items": [...],
  "totals": [...],

  "attribution": {
    "content_scope": "electronics-reviews-mix",
    "prior_session_ids": ["550e8400-e29b-41d4-a716-446655440999"],
    "content_retrieved": [
      {
        "content_url": "https://www.wirecutter.com/reviews/best-wireless-headphones",
        "timestamp": "2026-01-15T10:30:01Z"
      },
      {
        "content_url": "https://www.rtings.com/headphones/reviews/best-noise-cancelling",
        "timestamp": "2026-01-15T10:30:01Z"
      }
    ],
    "content_cited": [
      {
        "content_url": "https://www.wirecutter.com/reviews/best-wireless-headphones",
        "timestamp": "2026-01-15T10:30:05Z",
        "citation_type": "paraphrase",
        "excerpt_tokens": 85,
        "position": "primary"
      }
    ],
    "conversation_summary": {
      "turn_count": 3,
      "primary_intent": "comparison",
      "topics": ["headphones", "noise-cancelling", "Sony WH-1000XM5"],
      "total_content_retrieved": 5,
      "total_content_cited": 2
    }
  }
}
```

## Fields

### `attribution.content_scope`

Opaque identifier for the content collection used. Meaning is implementer-defined:

| Implementation | Example Value |
|----------------|---------------|
| Content mix platform | `"electronics-reviews-mix"` |
| API key scoped | `"apikey_abc123"` |
| Agreement ID | `"agreement_456"` |

### `attribution.prior_session_ids`

Links this checkout to previous sessions in the user journey. Enables attribution across multi-day purchase paths:

```
Day 1: Research session (Session A) — user browses headphone reviews
Day 3: Comparison session (Session B) — user narrows to 2 options
Day 7: Purchase session (Session C) — user completes checkout

Session C.prior_session_ids = ["session_a_id", "session_b_id"]
```

Attribution algorithms can distribute credit across the full journey rather than just the converting session.

### `attribution.content_retrieved`

Content fetched during the session. Captures correlation (content was available) without claiming causation (content was used).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content_url` | string (URI) | Yes | URL of the content retrieved |
| `timestamp` | datetime | Yes | When retrieved (UTC) |

### `attribution.content_cited`

Content explicitly referenced in agent responses. Includes quality signals for more accurate attribution:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content_url` | string (URI) | Yes | URL of the content cited |
| `timestamp` | datetime | Yes | When cited (UTC) |
| `citation_type` | enum | No | How content was used |
| `excerpt_tokens` | integer | No | Token count of excerpt |
| `position` | enum | No | Prominence in response |
| `content_hash` | string | No | SHA256 for verification |

#### Citation Types

| Type | Description |
|------|-------------|
| `direct_quote` | Verbatim or near-verbatim |
| `paraphrase` | Restated in different words |
| `reference` | Mentioned without quoting |
| `contradiction` | Retrieved but disagreed with |

These are agent-reported metadata describing how content appeared in a response. How each type is weighted for attribution is left to the consuming analytics platform.

#### Position

| Position | Description |
|----------|-------------|
| `primary` | Main basis for the response |
| `supporting` | Additional evidence |
| `mentioned` | Referenced but not relied upon |

### `attribution.conversation_summary`

Privacy-preserving aggregate of the conversation. Useful when full conversation context isn't available or shouldn't be shared.

## Negotiation

When agent and merchant both declare `org.openattribution.telemetry`:

1. Agent populates `attribution` object during checkout session
2. Merchant includes `attribution` in checkout response
3. On `checkout_completed`, attribution data flows to outcome

When only one party supports the extension:

- **Agent supports, merchant doesn't:** Agent can still collect telemetry client-side for its own attribution
- **Merchant supports, agent doesn't:** Merchant receives checkout without `attribution` object; no server-side attribution data

Graceful degradation: the checkout proceeds normally regardless. Attribution is additive, not blocking.

## Privacy Considerations

### Data Minimisation

- `conversation_summary` provides attribution signals without raw conversation text
- `content_scope` is opaque — doesn't reveal content collection contents
- `external_id` in user context should be hashed, not PII

### Privacy Levels

For implementations that need more granular control, the full OpenAttribution spec defines privacy levels (`full`, `summary`, `intent`, `minimal`). This extension uses `summary`-equivalent data by default.

## Relationship to OpenAttribution Telemetry Spec

This extension is a UCP binding of [OpenAttribution Telemetry v0.4](https://openattribution.org/telemetry). The standalone spec supports:

- Non-UCP contexts (direct API, MCP tools)
- Full conversation turn data with privacy levels
- Agent-to-agent session linking

This extension takes the commerce-relevant subset and packages it for UCP's `allOf` composition model.

## Example: Full Checkout with Attribution

```json
{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": [
      { "name": "dev.ucp.shopping.checkout", "version": "2026-01-11" },
      { "name": "org.openattribution.telemetry", "version": "2026-02-11" }
    ]
  },
  "id": "chk_headphones_purchase",
  "status": "completed",
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "id": "sony_wh1000xm5",
        "title": "Sony WH-1000XM5 Wireless Headphones",
        "price": 34999
      },
      "quantity": 1
    }
  ],
  "totals": [
    { "type": "subtotal", "amount": 34999 },
    { "type": "total", "amount": 34999 }
  ],
  "currency": "USD",

  "attribution": {
    "content_scope": "electronics-reviews",
    "prior_session_ids": ["440e8400-e29b-41d4-a716-446655440999"],
    "content_retrieved": [
      {
        "content_url": "https://www.wirecutter.com/reviews/best-wireless-headphones",
        "timestamp": "2026-01-15T10:30:01Z"
      },
      {
        "content_url": "https://www.rtings.com/headphones/reviews/best-noise-cancelling",
        "timestamp": "2026-01-15T10:30:01Z"
      },
      {
        "content_url": "https://www.soundguys.com/best-noise-cancelling-headphones-2024",
        "timestamp": "2026-01-15T10:31:00Z"
      }
    ],
    "content_cited": [
      {
        "content_url": "https://www.wirecutter.com/reviews/best-wireless-headphones",
        "timestamp": "2026-01-15T10:30:05Z",
        "citation_type": "paraphrase",
        "excerpt_tokens": 85,
        "position": "primary",
        "content_hash": "sha256:a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890"
      },
      {
        "content_url": "https://www.rtings.com/headphones/reviews/best-noise-cancelling",
        "timestamp": "2026-01-15T10:30:05Z",
        "citation_type": "reference",
        "position": "supporting"
      }
    ],
    "conversation_summary": {
      "turn_count": 4,
      "primary_intent": "comparison",
      "topics": ["headphones", "noise-cancelling", "Sony", "Bose", "battery life"],
      "total_content_retrieved": 3,
      "total_content_cited": 2
    }
  }
}
```

## Implementation Notes

### For Agent Developers

1. Check merchant profile for `org.openattribution.telemetry` support
2. If supported, populate `attribution` during checkout session
3. Track content retrieval and citation during conversation
4. Include `prior_session_ids` if user has prior sessions in their journey

### For Merchants

1. Declare capability in `/.well-known/ucp` profile
2. Accept and store `attribution` from checkout requests
3. Include `attribution` in checkout responses
4. Forward to attribution system on `checkout_completed`

### For Attribution Systems

1. Consume `attribution` data from completed checkouts
2. Use `content_cited` with quality signals for weighted attribution
3. Use `prior_session_ids` for journey-based attribution
4. Aggregate by `content_scope` for mix-level analytics

## Changelog

### 2026-02-11 (Draft)

- Initial extension specification
- Based on OpenAttribution Telemetry v0.4
- Extends `dev.ucp.shopping.checkout`
