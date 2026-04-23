# OpenAttribution Content Attribution for ACP

**Extension Name:** `content_attribution`
**Version:** `2026-02-15`
**Status:** Draft

## What This Is

Content attribution tracks which content URLs an AI shopping agent retrieved and cited during a purchase conversation. This enables merchants and affiliate networks to attribute purchases to the content that influenced the buying decision.

## How It Complements `affiliate_attribution`

ACP's existing `affiliate_attribution` handles network-level attribution with pre-wired content owner mappings. Content attribution provides the complementary content-level layer:

- **`affiliate_attribution`**: "This purchase came through content owner X on network Y" (requires prior setup)
- **`content_attribution`**: "The agent read and cited these URLs during the conversation" (no prior setup needed)

Together they solve the bootstrapping problem for agentic commerce attribution.

### URL-to-content-owner resolution flow

1. Agent retrieves content from various URLs during the shopping conversation
2. Agent records retrieved and cited URLs in the `content_attribution` object
3. Agent includes `content_attribution` in the ACP checkout request
4. Merchant receives the checkout and forwards `content_attribution` to their affiliate network
5. Affiliate network resolves content URLs against its content owner registry
6. Network identifies which content owners created the cited content
7. Standard affiliate commission crediting applies to the identified content owners

## Directory Contents

| File | Description |
|------|-------------|
| `rfc.content_attribution.md` | RFC (SEP format) -- full specification |
| `schemas/content_attribution.json` | JSON Schema (Draft 2020-12) for the extension |
| `examples/create_checkout_with_attribution.json` | Checkout request with content attribution |
| `examples/combined_affiliate_and_content.json` | Checkout with both affiliate and content attribution |

## Links

- [OpenAttribution Telemetry Specification v0.1](../SPECIFICATION.md)
- [OpenAttribution Telemetry Repository](https://github.com/openattribution-org/telemetry)
- [Agentic Commerce Protocol](https://www.agenticcommerce.dev/)
