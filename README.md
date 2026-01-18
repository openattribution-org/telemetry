# OpenAttribution

An open standard for tracking content attribution in AI agent interactions.

## What is OpenAttribution?

OpenAttribution is a cross-industry initiative to establish transparency in how AI agents use content. It provides:

- **A standard schema** for telemetry events across the content lifecycle
- **Privacy controls** for conversation data sharing
- **Session-based tracking** linking content to user outcomes

The goal: give publishers, brands, and platforms the signals needed to understand content influence and enable fair compensation - without mandating how that compensation works.

### What OpenAttribution Is Not

We keep the scope limited to attribution signals and transparency. OpenAttribution does **not**:

- Establish compensation structures
- Control or monetize content or attribution data
- Define specific attribution algorithms

Usage of the signals is up to the organizations and technologies that receive them.

### Ecosystem Context

OpenAttribution is designed to complement emerging standards like Google's [Universal Commerce Protocol (UCP)](https://github.com/Universal-Commerce-Protocol). Where UCP standardizes the transaction flow (discovery, checkout, payments), OpenAttribution provides the telemetry layer that captures content usage signals - enabling downstream attribution and compensation.

## Installation

```bash
pip install openattribution
```

Or with uv:

```bash
uv add openattribution
```

## Quick Start

```python
import asyncio
from uuid import uuid4

from openattribution import (
    OpenAttributionClient,
    ConversationTurn,
    SessionOutcome,
    UserContext,
)

async def main():
    async with OpenAttributionClient(
        endpoint="https://api.example.com/telemetry",
        api_key="your-api-key"
    ) as client:

        # Start a session
        session_id = await client.start_session(
            mix_id="my-content-mix",
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
                value_amount=9999,
                currency="USD",
            )
        )

asyncio.run(main())
```

## Event Types

**Content Events:**
- `content_retrieved` - Content fetched from source
- `content_displayed` - Content shown to user
- `content_engaged` - User interacted with content
- `content_cited` - Content referenced in response

**Conversation Events:**
- `turn_started` - User initiated a conversation turn
- `turn_completed` - Agent finished responding

**Commerce Events:**
- `product_viewed`, `product_compared`
- `cart_add`, `cart_remove`
- `checkout_started`, `checkout_completed`, `checkout_abandoned`

## Privacy Levels

Control what conversation data is shared based on trust relationships:

| Level | Text | Intent | Topics | Tokens | Content IDs |
|-------|------|--------|--------|--------|-------------|
| `full` | Yes | Yes | Yes | Yes | Yes |
| `summary` | Summarized | Yes | Yes | Yes | Yes |
| `intent` | No | Yes | Yes | Yes | Yes |
| `minimal` | No | No | No | Yes | Yes |

## Integration Patterns

### MCP Tool Integration

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

### Agent Integration

For agents you build directly, see the full example in [SPECIFICATION.md](./SPECIFICATION.md).

## Documentation

- [SPECIFICATION.md](./SPECIFICATION.md) - Full protocol specification
- [schema.json](./schema.json) - JSON Schema for cross-language implementation

## Get Involved

OpenAttribution is a community effort. We welcome:

- **Feedback** on the specification via [GitHub Issues](https://github.com/narrativai/openattribution/issues)
- **Implementations** in other languages
- **Use cases** we haven't considered

For information about joining the OpenAttribution initiative, visit [openattribution.org](https://openattribution.org).

## License

Apache 2.0 - see [LICENSE](./LICENSE) for details.
