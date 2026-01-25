# OpenAttribution Telemetry

[![PyPI version](https://badge.fury.io/py/openattribution-telemetry.svg)](https://badge.fury.io/py/openattribution-telemetry)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**SDK for AI content attribution telemetry - track what content influenced outcomes.**

Part of the [OpenAttribution](https://openattribution.org) project.

## What is OpenAttribution?

OpenAttribution is a cross-industry initiative enabling transparency in how AI agents use content. The standard defines **what signals to emit**, not how to use them - attribution algorithms, compensation structures, and business arrangements remain your domain.

| Standard | Question It Answers |
|----------|---------------------|
| **OpenAttribution Telemetry** | What content influenced this outcome? |
| **[OpenAttribution AIMS](https://github.com/openattribution-org/aims)** | What can this AI legally access? |

## Installation

```bash
pip install openattribution-telemetry
```

Or with uv:

```bash
uv add openattribution-telemetry
```

## Quick Start

```python
import asyncio
from uuid import uuid4

from openattribution.telemetry import (
    Client,
    ConversationTurn,
    SessionOutcome,
    UserContext,
)

async def main():
    async with Client(
        endpoint="https://api.example.com/telemetry",
        api_key="your-api-key"
    ) as client:

        # Start a session
        session_id = await client.start_session(
            content_scope="my-content-mix",
            user_context=UserContext(segments=["premium"])
        )

        # Record content retrieval
        content_id = uuid4()
        await client.record_event(
            session_id=session_id,
            event_type="content_retrieved",
            content_id=content_id,
        )

        # Record a conversation turn with privacy controls
        await client.record_event(
            session_id=session_id,
            event_type="turn_completed",
            turn=ConversationTurn(
                privacy_level="intent",
                query_intent="product_research",
                response_type="recommendation",
                topics=["headphones", "wireless"],
                content_ids_cited=[content_id],
                response_tokens=150,
            )
        )

        # End session with outcome
        await client.end_session(
            session_id=session_id,
            outcome=SessionOutcome(
                type="conversion",
                value_amount=9999,  # $99.99 in cents
                currency="USD",
            )
        )

asyncio.run(main())
```

## Session Model

A **Session** represents a bounded interaction between an end user and an AI agent:

```
Session
├── started_at
├── content_scope (opaque content collection identifier)
├── manifest_ref (optional AIMS reference)
├── prior_session_ids (for multi-session journeys)
├── user_context (segments, attributes)
├── events[]
│   ├── content_retrieved
│   ├── content_cited
│   ├── turn_completed
│   └── ...
├── ended_at
└── outcome (conversion / abandonment / browse)
```

## Event Types

**Content Events** track the content lifecycle:

| Event | Description |
|-------|-------------|
| `content_retrieved` | Content fetched from source |
| `content_displayed` | Content shown to user |
| `content_engaged` | User interacted with content |
| `content_cited` | Content referenced in response |

**Conversation Events** capture agent interactions:

| Event | Description |
|-------|-------------|
| `turn_started` | User initiated a conversation turn |
| `turn_completed` | Agent finished responding |

**Commerce Events** enable purchase attribution:

| Event | Description |
|-------|-------------|
| `product_viewed` | Product page viewed |
| `product_compared` | Products compared |
| `cart_add` / `cart_remove` | Cart modifications |
| `checkout_started` | Checkout initiated |
| `checkout_completed` | Purchase completed |
| `checkout_abandoned` | Checkout abandoned |

## Privacy Levels

Control what conversation data is shared based on trust relationships:

| Level | Query/Response Text | Intent | Topics | Tokens | Content IDs |
|-------|---------------------|--------|--------|--------|-------------|
| `full` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `summary` | Summarized | ✓ | ✓ | ✓ | ✓ |
| `intent` | ✗ | ✓ | ✓ | ✓ | ✓ |
| `minimal` | ✗ | ✗ | ✗ | ✓ | ✓ |

## MCP Tool Integration

Expose attribution as an MCP tool:

```python
@server.tool()
async def record_attribution(
    content_ids: list[str],
    query_intent: str,
    response_type: str,
) -> str:
    """Record content attribution for this conversation turn."""
    await client.record_event(
        session_id=current_session_id,
        event_type="turn_completed",
        turn=ConversationTurn(
            privacy_level="intent",
            query_intent=query_intent,
            response_type=response_type,
            content_ids_cited=[UUID(cid) for cid in content_ids],
        )
    )
    return "Attribution recorded"
```

## Related Standards

- **[SPECIFICATION.md](./SPECIFICATION.md)** - Full protocol specification
- **[schema.json](./schema.json)** - JSON Schema for cross-language implementations
- **[OpenAttribution AIMS](https://github.com/openattribution-org/aims)** - AI Manifest Standard for licensing and trust

## Get Involved

OpenAttribution is a community effort. We welcome:

- **Feedback** via [GitHub Issues](https://github.com/openattribution-org/telemetry/issues)
- **Implementations** in other languages
- **Use cases** we haven't considered

Visit [openattribution.org](https://openattribution.org) for more information.

## License

Apache 2.0 - see [LICENSE](./LICENSE) for details.
