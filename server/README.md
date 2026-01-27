# OpenAttribution Telemetry Server

**Reference server implementation for the OpenAttribution Telemetry standard.**

This is a complete, production-ready FastAPI server that implements the server-side of the [OpenAttribution Telemetry](https://github.com/openattribution-org/telemetry) protocol. Use it as:

- **Reference implementation** - Understand how to implement the server side
- **Starting point** - Fork and customize for your needs
- **Drop-in solution** - Deploy directly if it meets your requirements

## Installation

```bash
pip install openattribution-telemetry-server
```

Or with uv:

```bash
uv add openattribution-telemetry-server
```

## Quick Start

### 1. Set up PostgreSQL

Apply the migration to create the required tables:

```bash
psql $DATABASE_URL < migrations/001_telemetry_schema.sql
```

### 2. Configure Environment

```bash
export DATABASE_URL="postgresql://user:pass@localhost/mydb"
export PORT=8007  # Optional, defaults to 8007
```

### 3. Run the Server

```bash
uvicorn openattribution.telemetry_server.main:app --host 0.0.0.0 --port 8007
```

Or programmatically:

```python
from openattribution.telemetry_server.main import app
import uvicorn

uvicorn.run(app, host="0.0.0.0", port=8007)
```

## API Endpoints

### Public API (SDK-compatible)

These endpoints match the [openattribution-telemetry](https://pypi.org/project/openattribution-telemetry/) client SDK:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/session/start` | POST | Start a new session, returns `session_id` |
| `/events` | POST | Record one or more events |
| `/session/end` | POST | End session with outcome |
| `/health` | GET | Health check |

### Internal API (for Attribution Systems)

These endpoints are for downstream attribution processing:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/internal/sessions/{id}` | GET | Get session with all events |
| `/internal/sessions` | GET | List sessions with filters |
| `/internal/sessions/by-external-id/{id}` | GET | Look up by external ID |

**Query parameters for `/internal/sessions`:**
- `outcome_type` - Filter by outcome (conversion, abandonment, browse)
- `content_scope` - Filter by content scope
- `since` / `until` - Time range filter on `ended_at`
- `limit` / `offset` - Pagination

## Usage with Client SDK

```python
from openattribution.telemetry import Client, SessionOutcome
from uuid import uuid4

async with Client(
    endpoint="http://localhost:8007",
    api_key="your-api-key"  # Implement your own auth
) as client:
    # Start session
    session_id = await client.start_session(
        content_scope="my-content-collection",
        external_session_id="user-abc123",
    )

    # Record events
    await client.record_event(
        session_id=session_id,
        event_type="content_retrieved",
        content_id=uuid4()
    )

    # End with outcome
    await client.end_session(
        session_id=session_id,
        outcome=SessionOutcome(type="conversion", value_amount=4999)
    )
```

## Database Schema

The server uses two tables:

**sessions** - Telemetry sessions
```sql
- id (UUID, primary key)
- content_scope (TEXT) - Opaque content collection identifier
- manifest_ref (TEXT) - Optional AIMS manifest reference
- agent_id (TEXT) - Agent identifier
- external_session_id (TEXT) - Your session ID for lookups
- prior_session_ids (UUID[]) - Cross-session journey linking
- user_context (JSONB) - User segments and attributes
- started_at / ended_at (TIMESTAMPTZ)
- outcome_type (TEXT) - conversion/abandonment/browse
- outcome_value (JSONB) - Full outcome data
```

**events** - Session events
```sql
- id (UUID, primary key)
- session_id (UUID, foreign key)
- event_type (TEXT) - Standard event types
- content_id (UUID) - Referenced content
- product_id (UUID) - Referenced product
- turn_data (JSONB) - Conversation turn data
- event_data (JSONB) - Additional metadata
- event_timestamp (TIMESTAMPTZ)
```

## Customization

### Adding Authentication

The reference implementation doesn't include authentication. Add your own:

```python
from fastapi import Depends, HTTPException, Header
from openattribution.telemetry_server.main import app

async def verify_api_key(x_api_key: str = Header(...)):
    if not is_valid_key(x_api_key):
        raise HTTPException(401, "Invalid API key")
    return x_api_key

# Apply to routes
app.dependency_overrides[...] = verify_api_key
```

### Extending the Schema

Fork and add your own fields to the migration. The server uses standard psycopg3, so extending is straightforward.

### Custom Event Processing

Override the event service to add custom processing:

```python
from openattribution.telemetry_server.services import events

# Add hooks, validation, or side effects
original_create = events.create_events

async def create_events_with_hook(conn, session_id, events_list):
    result = await original_create(conn, session_id, events_list)
    await my_custom_processing(result)
    return result

events.create_events = create_events_with_hook
```

## Docker

```dockerfile
FROM python:3.13-slim

RUN pip install openattribution-telemetry-server

EXPOSE 8007
CMD ["uvicorn", "openattribution.telemetry_server.main:app", "--host", "0.0.0.0", "--port", "8007"]
```

## License

Apache 2.0 - see [LICENSE](../LICENSE) for details.
