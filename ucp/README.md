# OpenAttribution Telemetry — UCP Integration

This directory contains [Universal Commerce Protocol](https://ucp.dev) integration for OpenAttribution Telemetry.

## Two Approaches

OpenAttribution Telemetry integrates with UCP in two complementary ways:

### 1. Checkout Extension (embedded attribution)

Embeds attribution data directly into UCP checkout sessions using `allOf` composition:

```json
{
  "id": "chk_123",
  "line_items": [...],
  "attribution": {
    "content_scope": "electronics-reviews",
    "content_cited": [...]
  }
}
```

**Use when:** Attribution flows naturally with checkout. Simpler for merchants already implementing UCP checkout.

**Files:** `EXTENSION.md`, `extension-schema.json`

### 2. Standalone Capability (session lifecycle)

Independent REST/MCP endpoints for full session lifecycle management:

```
POST /telemetry/sessions              # Start session
POST /telemetry/sessions/{id}/events  # Record events
POST /telemetry/sessions/{id}/outcome # End with outcome
```

**Use when:**
- Tracking browse sessions without checkout
- Multi-agent attribution chains
- Conversation analytics beyond commerce
- Integration with non-UCP agents

**Files:** `org.openattribution.telemetry.yaml`, `schemas/telemetry.json`

Both approaches share the same underlying schema (OpenAttribution Telemetry v0.4) and are interoperable. Merchants and agents can support either or both.

## Files

| File | Description |
|------|-------------|
| `EXTENSION.md` | Checkout extension specification |
| `extension-schema.json` | JSON Schema for checkout extension |
| `org.openattribution.telemetry.yaml` | Standalone capability specification |
| `schemas/telemetry.json` | JSON Schema for standalone capability |

## Quick Start

### Option A: Checkout Extension

1. Declare capability in your UCP profile:

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
        "spec": "https://openattribution.org/telemetry/ucp/extension",
        "schema": "https://openattribution.org/telemetry/ucp/schemas/extension.json",
        "extends": "dev.ucp.shopping.checkout"
      }
    ]
  }
}
```

2. Add `attribution` object to checkout sessions (see `EXTENSION.md`)

### Option B: Standalone Capability

1. Declare capability:

```json
{
  "ucp": {
    "capabilities": [
      {
        "name": "org.openattribution.telemetry",
        "version": "2026-02-11",
        "spec": "https://openattribution.org/telemetry/ucp/extension",
        "schema": "https://openattribution.org/telemetry/ucp/schemas/telemetry.json"
      }
    ]
  }
}
```

2. Use session lifecycle endpoints (see `org.openattribution.telemetry.yaml`)

## Integration with Other Capabilities

### With Content Search Capabilities

When using a content search capability for content discovery:

1. Start telemetry session at conversation start
2. After each search, record `content_retrieved` events
3. When content is cited in responses, record `content_cited` events
4. At conversation end, record the outcome (with optional `checkout_id`)

## Relationship to Standalone SDK

The UCP integration is a standards-based binding. The [standalone SDK](../README.md) supports:

- Non-UCP contexts (direct API, MCP tools)
- Full conversation turn tracking with privacy levels
- Agent-to-agent session linking
- Bulk session upload

Use UCP integration for interoperability with other UCP-compatible agents and merchants. Use the SDK directly when UCP isn't in the picture.

## Namespace Strategy

OpenAttribution Telemetry uses the `org.openattribution.*` vendor namespace, following UCP's governance model for vendor extensions. Per [UCP CONTRIBUTING.md](https://github.com/Universal-Commerce-Protocol/ucp/blob/main/CONTRIBUTING.md): vendors should first create capabilities and extensions in vendor-specific namespace patterns for new use cases.

The vendor extension approach allows us to:
- Ship immediately with a reference implementation
- Iterate based on real-world usage
- Pursue TC approval for core inclusion once adoption is proven

## Status

| Spec | Version | Status |
|------|---------|--------|
| Checkout Extension | 2026-02-11 | Draft |
| Standalone Capability | 2026-02-11 | Draft |
