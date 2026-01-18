# OpenAttribution

An open standard for tracking content attribution in AI agent interactions.

## What is OpenAttribution?

OpenAttribution is a cross-industry initiative of publishers, brands, and technology providers working towards transparency in how AI agents use content.

The standard defines **what signals to emit**, not how to use them. Attribution algorithms, compensation structures, and business arrangements remain the domain of individual organizations.

**What we provide:**

- A minimal, extensible schema for telemetry events across the content lifecycle
- Privacy tiers for conversation data sharing based on trust relationships
- Session-based tracking linking content influence to user outcomes

**What we don't do:**

- Establish compensation structures
- Control or monetize content or attribution data
- Define specific attribution algorithms

## Ecosystem Context

OpenAttribution complements emerging standards like Google's [Universal Commerce Protocol (UCP)](https://github.com/Universal-Commerce-Protocol).

| Standard | Question It Answers |
|----------|---------------------|
| **UCP** | How does an agent complete a purchase? |
| **OpenAttribution** | What content influenced that purchase? |

Where UCP standardizes the transaction flow (discovery, checkout, payments), OpenAttribution provides the telemetry layer that captures content usage signals—enabling downstream attribution and compensation.

## The Standard

### Session Model

A **Session** represents a bounded interaction between an end user and an AI agent:

```
Session
├── started_at
├── mix_id (content collection identifier)
├── user_context (segments, attributes)
├── events[]
│   ├── content_retrieved
│   ├── content_cited
│   ├── turn_completed
│   └── ...
├── ended_at
└── outcome (conversion / abandonment / browse)
```

### Event Types

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

### Privacy Levels

Control what conversation data is shared based on trust relationships:

| Level | Query/Response Text | Intent | Topics | Tokens | Content IDs |
|-------|---------------------|--------|--------|--------|-------------|
| `full` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `summary` | Summarized | ✓ | ✓ | ✓ | ✓ |
| `intent` | ✗ | ✓ | ✓ | ✓ | ✓ |
| `minimal` | ✗ | ✗ | ✗ | ✓ | ✓ |

### Documentation

- **[SPECIFICATION.md](./SPECIFICATION.md)** — Full protocol specification
- **[schema.json](./schema.json)** — JSON Schema for cross-language implementation

## Reference Implementation (Python)

A Python SDK is provided as a reference implementation.

### Installation

```bash
pip install openattribution
```

Or with uv:

```bash
uv add openattribution
```

### Quick Start

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

## Get Involved

OpenAttribution is a community effort. We welcome:

- **Feedback** on the specification via [GitHub Issues](https://github.com/narrativai/openattribution/issues)
- **Implementations** in other languages
- **Use cases** we haven't considered

For information about joining the OpenAttribution initiative, visit [openattribution.org](https://openattribution.org).

## License

Apache 2.0 — see [LICENSE](./LICENSE) for details.
