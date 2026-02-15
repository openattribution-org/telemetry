# Enhancement Proposal: Content Citation and Attribution Telemetry

## Summary

`org.openattribution.telemetry` is a vendor extension that tracks which content influenced AI agent outcomes in commerce conversations. It embeds an `attribution` object in UCP checkout sessions, recording which content was retrieved and cited during the conversation that led to a purchase.

This starts as a vendor extension under the `org.openattribution.*` namespace, per UCP's governance model for new use cases.

## Motivation

AI shopping agents use reviews, guides, comparisons, and other licensed content to generate product recommendations. There is no standardized way to:

1. Track which content was retrieved and cited in a response that led to a purchase
2. Attribute commerce outcomes (purchases, cart additions) to specific content pieces
3. Preserve user privacy while providing attribution signals to content creators
4. Link multi-session journeys where research, comparison, and purchase happen across separate conversations

Without this, content creators have no visibility into their contribution to commerce outcomes, merchants cannot measure content partnership ROI, and attribution algorithms have no standardized signal to work with.

## Goals

* Define an optional attribution extension that embeds content citation data in UCP checkout sessions
* Support privacy-preserving data sharing with four granularity levels (`full`, `summary`, `intent`, `minimal`)
* Enable cross-session attribution for multi-day purchase journeys via `prior_session_ids`
* Support negative attribution via `contradiction` citation type (content retrieved but disagreed with)
* Provide citation quality signals (`citation_type`, `excerpt_tokens`, `position`, `content_hash`) for weighted attribution

## Non-Goals

* Defining specific attribution algorithms (left to implementers)
* Mandating payment structures or compensation models
* Requiring specific privacy policies (left to agreements between parties)

## Detailed Design

### Capability Declaration

```json
{
  "capabilities": [
    {
      "name": "org.openattribution.telemetry",
      "version": "2026-02-11",
      "spec": "https://openattribution.org/ucp/telemetry",
      "schema": "https://openattribution.org/ucp/schemas/extension.json",
      "extends": "dev.ucp.shopping.checkout"
    }
  ]
}
```

### Checkout Extension

Adds an `attribution` object to UCP checkout sessions:

```json
{
  "id": "chk_123",
  "line_items": ["..."],
  "attribution": {
    "content_scope": "electronics-reviews",
    "prior_session_ids": ["550e8400-e29b-41d4-a716-446655440999"],
    "content_retrieved": [
      {
        "content_id": "770e8400-e29b-41d4-a716-446655440010",
        "timestamp": "2026-01-15T10:30:01Z",
        "source_id": "wirecutter.com"
      }
    ],
    "content_cited": [
      {
        "content_id": "770e8400-e29b-41d4-a716-446655440010",
        "timestamp": "2026-01-15T10:30:05Z",
        "citation_type": "paraphrase",
        "excerpt_tokens": 85,
        "position": "primary"
      }
    ],
    "conversation_summary": {
      "turn_count": 3,
      "primary_intent": "comparison",
      "topics": ["headphones", "noise-cancelling"],
      "total_content_retrieved": 5,
      "total_content_cited": 2
    }
  }
}
```

### Key Schema Elements

**Citation Types**

How content appeared in a response (agent-reported):

| Type | Description |
|------|-------------|
| `direct_quote` | Verbatim or near-verbatim |
| `paraphrase` | Restated in different words |
| `reference` | Mentioned without quoting |
| `contradiction` | Retrieved but disagreed with |

These are raw metadata. How much weight each type carries for attribution is left to the consuming analytics platform.

**Privacy Levels**

Control data sharing granularity:

| Level | Query/Response | Intent | Topics | Tokens | Content IDs |
|-------|---------------|--------|--------|--------|-------------|
| `full` | Yes | Yes | Yes | Yes | Yes |
| `summary` | Summarized | Yes | Yes | Yes | Yes |
| `intent` | No | Yes | Yes | Yes | Yes |
| `minimal` | No | No | No | Yes | Yes |

**Cross-Session Attribution**

`prior_session_ids` links sessions into multi-day purchase journeys, allowing attribution algorithms to distribute credit across the full path from research to conversion.

### Negotiation

* When both agent and merchant declare `org.openattribution.telemetry`: full bidirectional attribution flow
* When only one party supports it: graceful degradation. Checkout proceeds normally; attribution is additive, not blocking.

## Risks and Mitigations

**Privacy risk:** Conversation data could leak through attribution signals.
* *Mitigation:* Four privacy levels with clear field-gating rules. Default to `minimal`. `conversation_summary` provides attribution without raw text. `external_id` must be opaque (not PII).

**Adoption risk:** Vendor extension may not gain traction.
* *Mitigation:* Open-source reference implementation (Apache 2.0), Python SDK, and reference server lower the barrier.

**Schema evolution risk:** Breaking changes could fragment implementations.
* *Mitigation:* Schema version field (`0.3`) and date-based capability versions (`2026-02-11`). Deprecation policy requires 6 months notice.

## Test Plan

**Unit tests:**
* Schema validation for all models (session, event, outcome, conversation turn)
* Privacy level field gating (ensure `minimal` excludes text fields)
* Citation type and position enum validation

**Integration tests:**
* Checkout extension: `attribution` object in checkout request/response
* Cross-session linking via `prior_session_ids`
* Capability negotiation: graceful degradation when only one party supports extension

**End-to-end tests:**
* Shopping conversation with content retrieval, citation, and purchase
* Privacy level enforcement across the full flow

## Graduation Criteria

**Working Draft to Candidate:**

- [ ] Vendor extension schema published and documented
- [ ] At least one reference implementation with passing tests
- [ ] Initial adoption by at least two independent agent or merchant implementations
- [ ] Feedback period (minimum 3 months) with no breaking issues reported
- [ ] TC majority vote to advance

**Candidate to Stable:**

- [ ] Adoption feedback collected and addressed from production deployments
- [ ] At least two independent, interoperable implementations demonstrating the extension
- [ ] Full documentation and migration guides published
- [ ] Interoperability testing between independent implementations
- [ ] TC majority vote to advance

## Implementation History

* 2026-02-11: Initial vendor extension specification drafted
* 2026-02-15: Reference implementation published (Python SDK, FastAPI server, JSON Schemas)

## References

* [openattribution-org/telemetry](https://github.com/openattribution-org/telemetry) (repository)
* [SPECIFICATION.md](https://github.com/openattribution-org/telemetry/blob/main/SPECIFICATION.md) (OpenAttribution Telemetry v0.3)
* [schema.json](https://github.com/openattribution-org/telemetry/blob/main/schema.json) (JSON Schema)
* [ucp/EXTENSION.md](https://github.com/openattribution-org/telemetry/blob/main/ucp/EXTENSION.md) (UCP checkout extension spec)
