# OpenAttribution

An open standard and Python SDK for tracking content attribution in AI agent interactions.

## Overview

OpenAttribution enables fair compensation for content creators when their content is used by AI agents to generate valuable responses. It provides:

- **A standard schema** for telemetry events across the content lifecycle
- **Privacy controls** for conversation data sharing
- **Session-based tracking** linking content to user outcomes

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
from datetime import datetime, UTC

from openattribution import (
    OpenAttributionClient,
    TelemetryEvent,
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
        await client.record_event(
            session_id=session_id,
            event_type="content_retrieved",
            content_id=uuid4(),
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

## Schema Overview

### Sessions

A session represents a user's interaction with an AI agent:

```python
from openattribution import TelemetrySession

session = TelemetrySession(
    session_id=uuid4(),
    mix_id="electronics-reviews",
    agent_id="shopping-assistant",
    started_at=datetime.now(UTC),
    user_context=UserContext(segments=["returning"]),
)
```

### Events

Events track specific actions within a session:

```python
from openattribution import TelemetryEvent

# Content was retrieved
event = TelemetryEvent(
    id=uuid4(),
    type="content_retrieved",
    timestamp=datetime.now(UTC),
    content_id=article_uuid,
)

# Content was cited in response
event = TelemetryEvent(
    id=uuid4(),
    type="content_cited",
    timestamp=datetime.now(UTC),
    content_id=article_uuid,
    data={"citation_type": "direct_quote"},
)
```

### Event Types

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

### Conversation Turns

Capture query/response data with privacy controls:

```python
from openattribution import ConversationTurn

# Full text (highest trust)
turn = ConversationTurn(
    privacy_level="full",
    query_text="What are the best noise-cancelling headphones?",
    response_text="Based on recent reviews, the Sony WH-1000XM5...",
    content_ids_retrieved=[article1_id, article2_id],
    content_ids_cited=[article1_id],
)

# Intent only (privacy-preserving)
turn = ConversationTurn(
    privacy_level="intent",
    query_intent="comparison",
    response_type="recommendation",
    topics=["headphones", "noise-cancelling"],
    content_ids_cited=[article1_id],
)

# Minimal (just metadata)
turn = ConversationTurn(
    privacy_level="minimal",
    content_ids_retrieved=[article1_id, article2_id],
    content_ids_cited=[article1_id],
    query_tokens=12,
    response_tokens=150,
)
```

### Privacy Levels

| Level | Text | Intent | Topics | Tokens | Content IDs |
|-------|------|--------|--------|--------|-------------|
| `full` | Yes | Yes | Yes | Yes | Yes |
| `summary` | Summarized | Yes | Yes | Yes | Yes |
| `intent` | No | Yes | Yes | Yes | Yes |
| `minimal` | No | No | No | Yes | Yes |

### Outcomes

Capture session results for attribution:

```python
from openattribution import SessionOutcome

outcome = SessionOutcome(
    type="conversion",  # or "abandonment", "browse"
    value_cents=4999,
    currency="USD",
    products=[product_uuid],
)
```

## Integration Patterns

### MCP Tool Integration

When building an MCP server, expose attribution as a tool:

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

For agents you build directly:

```python
class AttributionAgent:
    def __init__(self, attribution_client: OpenAttributionClient):
        self.client = attribution_client
        self.session_id = None

    async def start_conversation(self, user_context: UserContext):
        self.session_id = await self.client.start_session(
            mix_id="my-mix",
            user_context=user_context,
        )

    async def process_turn(self, query: str) -> str:
        # Record turn start
        await self.client.record_event(
            session_id=self.session_id,
            event_type="turn_started",
            turn=ConversationTurn(
                privacy_level="full",
                query_text=query,
            )
        )

        # Retrieve content
        content_ids = await self.retrieve_content(query)
        for cid in content_ids:
            await self.client.record_event(
                session_id=self.session_id,
                event_type="content_retrieved",
                content_id=cid,
            )

        # Generate response
        response, cited_ids = await self.generate_response(query, content_ids)

        # Record turn completion
        await self.client.record_event(
            session_id=self.session_id,
            event_type="turn_completed",
            turn=ConversationTurn(
                privacy_level="full",
                query_text=query,
                response_text=response,
                content_ids_retrieved=content_ids,
                content_ids_cited=cited_ids,
            )
        )

        return response
```

## Specification

For the complete specification, see [SPECIFICATION.md](./SPECIFICATION.md).

## License

Apache 2.0 - see [LICENSE](./LICENSE) for details.
