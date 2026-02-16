# OpenAttribution Telemetry

[![PyPI version](https://badge.fury.io/py/openattribution-telemetry.svg)](https://badge.fury.io/py/openattribution-telemetry)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**Open signal format for AI content attribution. Track what content influenced outcomes.**

Part of the [OpenAttribution](https://openattribution.org) project.

## What is OpenAttribution?

OpenAttribution defines a **schema** for content attribution signals in AI agent interactions. It specifies the shape of the data, not how you move it. Your implementation chooses the transport: HTTP postback, SSE via MCP tool calls, message queues, direct database writes, whatever fits.

This repo contains:
- **Schema** (Pydantic models) for sessions, events, outcomes, and privacy levels
- **Python SDK client** for emitting signals over HTTP
- **Reference server** (FastAPI + PostgreSQL) for receiving and storing them
- **Commerce protocol integrations** for [UCP](https://ucp.dev) and [ACP](https://www.agenticcommerce.dev/)

See [SPECIFICATION.md](./SPECIFICATION.md) for the full protocol spec and [schema.json](./schema.json) for cross-language implementations.

## Installation

```bash
pip install openattribution-telemetry
```

Or with uv:

```bash
uv add openattribution-telemetry
```

## Quick Start (Python SDK)

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
        content_url = "https://www.wirecutter.com/reviews/best-wireless-headphones"
        await client.record_event(
            session_id=session_id,
            event_type="content_retrieved",
            content_url=content_url,
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
                content_urls_cited=[content_url],
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

### Bulk Upload

If your agent collects telemetry locally and uploads after the session ends, use `upload_session` to send everything in one request:

```python
from datetime import UTC, datetime
from uuid import uuid4

from openattribution.telemetry import (
    Client,
    SessionOutcome,
    TelemetryEvent,
    TelemetrySession,
)

session = TelemetrySession(
    session_id=uuid4(),
    initiator_type="agent",
    agent_id="my-agent",
    content_scope="my-content-mix",
    started_at=datetime.now(UTC),
    events=[
        TelemetryEvent(
            id=uuid4(),
            type="content_retrieved",
            timestamp=datetime.now(UTC),
            content_url="https://www.rtings.com/headphones/reviews/best-noise-cancelling",
        ),
    ],
    outcome=SessionOutcome(type="conversion", value_amount=9999),
)

async with Client(endpoint="https://api.example.com/telemetry", api_key="key") as client:
    server_session_id = await client.upload_session(session)
```

The server generates its own session ID and stores the caller's `session_id` as `external_session_id`.

## Session Model

A **session** tracks one interaction between a user (or agent) and an AI agent:

```
Session
├── started_at
├── content_scope (opaque content collection identifier)
├── manifest_ref (optional [AIMS](https://github.com/openattribution-org/aims) licence reference)
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

| Level | Query/Response Text | Intent | Topics | Tokens | Content URLs |
|-------|---------------------|--------|--------|--------|-------------|
| `full` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `summary` | Summarized | ✓ | ✓ | ✓ | ✓ |
| `intent` | ✗ | ✓ | ✓ | ✓ | ✓ |
| `minimal` | ✗ | ✗ | ✗ | ✓ | ✓ |

## Transport

OpenAttribution is transport-agnostic. The schema defines the signal shape; you pick how to deliver it.

| Pattern | When to use |
|---------|-------------|
| **HTTP postback** | Agent fires events to a telemetry endpoint during or after a session. The SDK client and reference server implement this. |
| **Bulk upload** | Agent collects signals locally, uploads a complete session after it ends. Good for batch pipelines or offline agents. |
| **MCP tool** | Agent exposes an MCP tool that records attribution inline during conversation turns. Works well with SSE-based MCP transports. |
| **Message queue** | High-throughput systems publish signals to Kafka, SQS, etc. Consumer writes to storage. |
| **Direct DB write** | Co-located systems skip HTTP and write session rows directly. |

### MCP Tool Example

Wrap the SDK client in an MCP tool so the agent records attribution as part of its normal tool-use flow:

```python
@server.tool()
async def record_attribution(
    content_urls: list[str],
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
            content_urls_cited=content_urls,
        )
    )
    return "Attribution recorded"
```

## Reference Server

A working server implementation lives in [`server/`](./server/):

```bash
pip install openattribution-telemetry-server
```

It provides:
- REST API matching the SDK client (`/session/start`, `/events`, `/session/end`)
- Bulk session upload (`POST /session/bulk`) for post-hoc reporting
- Internal query endpoints for attribution systems
- PostgreSQL storage

See [`server/README.md`](./server/README.md) for setup and deployment.

## UCP Integration

OpenAttribution integrates with the [Universal Commerce Protocol](https://ucp.dev) for standardised AI commerce attribution. Two approaches are available:

| Approach | Use Case |
|----------|----------|
| **Checkout extension** | Embed attribution in UCP checkout sessions |
| **Standalone capability** | Independent endpoints for full session lifecycle |

The SDK includes a bridge to convert telemetry sessions into UCP checkout attribution objects:

```python
from openattribution.telemetry import session_to_attribution

attribution = session_to_attribution(telemetry_session)
# Embed in UCP checkout payload
```

See [`ucp/README.md`](./ucp/README.md) for specifications and integration examples.

## ACP Integration

OpenAttribution integrates with the [Agentic Commerce Protocol](https://www.agenticcommerce.dev/) via a content attribution extension that complements ACP's existing `affiliate_attribution`.

The SDK includes a bridge to convert telemetry sessions into ACP content attribution objects:

```python
from openattribution.telemetry import session_to_content_attribution

content_attribution = session_to_content_attribution(telemetry_session)
# Include in ACP checkout request
```

See [`acp/README.md`](./acp/README.md) for the RFC, schema, and examples.

## Get Involved

OpenAttribution is a community effort. We welcome:

- **Feedback** via [GitHub Issues](https://github.com/openattribution-org/telemetry/issues)
- **Implementations** in other languages
- **Use cases** we haven't considered

Visit [openattribution.org](https://openattribution.org) for more information.

## License

Apache 2.0 - see [LICENSE](./LICENSE) for details.
