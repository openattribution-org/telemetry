# OpenAttribution Telemetry (retired)

> [!IMPORTANT]
> **This repository is retired and kept for reference.** The specification became the neutral **Content Telemetry** standard, stewarded by the SPUR Coalition:
>
> - **The standard** (specification, schemas, conformance tests): [SPUR-Coalition/telemetry](https://github.com/SPUR-Coalition/telemetry) - schemas resolve at [contenttelemetry.org](https://contenttelemetry.org). Open for public comment 12 June to 10 July 2026.
> - **Publisher profile**: [SPUR-Coalition/telemetry-profile](https://github.com/SPUR-Coalition/telemetry-profile)
> - **OpenAttribution commerce profile and the ACP/UCP bindings** (previously in `acp/` and `ucp/` here): [openattribution-org/commerce-profile](https://github.com/openattribution-org/commerce-profile)
> - **SDKs**: [telemetry-py](https://github.com/openattribution-org/telemetry-py), [telemetry-js](https://github.com/openattribution-org/telemetry-js)
>
> The contents below are the final pre-transfer state and are no longer maintained. OpenAttribution participates in the standard via public comment and maintains the commerce profile on it.

**Open signal format for content use in AI systems.**

When an AI agent uses content to generate a response, five things can happen - and today the content owner can only see one of them. This specification defines a schema for tracking all five, across any content type and any kind of agent.

The manifest format used to identify content owners, agents, and platforms is defined in [section 8 of the specification](./SPECIFICATION.md#8-manifest).

## What is OpenAttribution Telemetry

OpenAttribution Telemetry is a vendor-neutral framework for capturing how content flows through AI systems. It standardises the signals emitted when an agent retrieves, uses, references, or surfaces content - regardless of:

- **Content type.** Articles, products, videos, audio, code, documentation, research, datasets, social posts, reviews.
- **Agent.** Conversational assistants, search engines, commerce agents, research tools, recommendation systems, summarisers, coding copilots.
- **Deployment.** Browser-embedded, app-integrated, API-accessed, on-device, server-side.
- **Industry.** Publishing, commerce, education, media, software, science, enterprise knowledge.

The protocol is Apache 2.0 licensed and designed for multi-observer reporting - the same event can be reported independently by the content owner's infrastructure, the agent, and intermediaries, then correlated by attribution consumers.

## The problem

AI agents retrieve content, use it to generate responses, and sometimes cite it. Content owners currently see one signal: HTTP requests hitting their servers. Everything after that - whether the content actually influenced the response, whether it was cited, whether a user saw the citation, whether they clicked through - is invisible.

Platforms self-report usage metrics (if they report at all), and content owners have no way to verify the numbers or compare across platforms.

## The five stages

OpenAttribution tracks content through five stages:

```
Retrieved    →  content fetched over HTTP (content owner can see this today)
  Grounded   →  content loaded into the agent's generation context
    Cited    →  content explicitly referenced in the response
      Displayed  →  user saw the reference
        Engaged  →  user clicked, expanded, copied, or shared
```

Each stage is a progressively narrower subset. What ties them together is the **session** - a single user journey from query to outcome, identified by a session ID. When a user clicks through to a landing page, the agent passes an opaque click-token (`ctx_token`) rather than the session ID itself, which an attribution consumer resolves back to the originating session. That token is the thread that connects content to outcome across the click-out boundary.

The gaps between stages are where the interesting questions live:

- **Retrieval without grounding** - your content was fetched but not used
- **Grounding without citation** - your content influenced the answer but you got no credit
- **Citation without engagement** - your content was cited but the user didn't click through

The grounding event captures the boundary "this content entered the agent's generation context." It is architecture-neutral and decoupled from retrieval: content cached by the agent for days still produces a grounding event in every session it influences, even when the content owner's infrastructure sees nothing.

## Design principles

**Post-hoc, not pre-declared.** Events report what actually happened, not what the agent said it would do at request time. An agent cannot reliably declare how it will use content before reading it. Telemetry captures observed reality after the fact.

**Observable boundaries, not agent internals.** The five event types mark boundary crossings. What happens between them - the fan-out, relevance evaluation, re-ranking, reasoning chains - is internal to the agent and changes constantly. The spec does not model it.

**Multiple observers, one event.** A content retrieval can be reported by the content owner's CDN, the content owner's origin server, and the AI agent independently. The `Content-Telemetry-ID` header correlates these into a single corroborated event. Uncorroborated retrievals (no matching agent event) may indicate an agent that does not yet support the telemetry protocol.

**Privacy by default.** Four privacy levels control what conversation data is shared: from `full` (query and response text) down to `minimal` (token counts and content URLs only).

## What's in this repo

- [SPECIFICATION.md](./SPECIFICATION.md) - the full protocol specification
- [telemetry-session.json](./telemetry-session.json) - JSON Schema for session documents
- [telemetry-event.json](./telemetry-event.json) - JSON Schema for standalone event envelopes
- [manifest.json](./manifest.json) - JSON Schema for the `.well-known/content-telemetry.json` manifest ([section 8](./SPECIFICATION.md#8-manifest))
- [tests/](./tests/) - conformance test suite: valid/invalid fixtures plus `validate.py`
- [CONSIDERATIONS.md](./CONSIDERATIONS.md) - deferred items under consideration for future versions
- Adoption guides for content owners, platforms, marketplaces, and regulators live on [openattribution.org](https://openattribution.org)
- [acp/](./acp/) - Agentic Commerce Protocol content attribution extension
- [ucp/](./ucp/) - Universal Commerce Protocol checkout attribution extension

## Quick example

A user asks an AI agent about UK interest rates. The agent grounds its response in a cached Reuters article, cites it, and shows a link. The user reads the answer and leaves without clicking through.

```json
{
  "document_type": "session",
  "schema_version": "0.1",
  "session_id": "660e8400-e29b-41d4-a716-446655440000",
  "agent_id": "copilot-v3",
  "started_at": "2026-03-28T09:00:00Z",
  "events": [
    {
      "type": "content_grounded",
      "timestamp": "2026-03-28T09:00:00Z",
      "content_url": "https://www.reuters.com/article/abc123",
      "content_id": "reuters:abc123",
      "data": {
        "scope": "session",
        "cached": true,
        "tokens_ingested": 3200,
        "content_last_modified": "2026-03-27T18:30:00Z"
      }
    },
    {
      "type": "turn_started",
      "timestamp": "2026-03-28T09:00:01Z",
      "turn_id": "1",
      "turn": {
        "privacy_level": "intent",
        "query_intent": "question",
        "topics": ["UK economy", "interest rates"]
      }
    },
    {
      "type": "content_cited",
      "timestamp": "2026-03-28T09:00:05Z",
      "turn_id": "1",
      "content_url": "https://www.reuters.com/article/abc123",
      "content_id": "reuters:abc123",
      "data": {
        "citation_type": "paraphrase",
        "position": "primary"
      }
    },
    {
      "type": "content_displayed",
      "timestamp": "2026-03-28T09:00:05Z",
      "turn_id": "1",
      "content_url": "https://www.reuters.com/article/abc123",
      "content_id": "reuters:abc123",
      "data": { "display_type": "link" }
    },
    {
      "type": "turn_completed",
      "timestamp": "2026-03-28T09:00:05Z",
      "turn_id": "1",
      "turn": {
        "privacy_level": "intent",
        "response_mode": "standard",
        "response_tokens": 280,
        "ad_rendered": true
      }
    }
  ]
}
```

No `content_retrieved` event - the article was cached from a previous fetch. The content owner's infrastructure saw nothing. The grounding event is the only signal that content was used.

The content owner can derive: Reuters article `abc123` was in context for the response, cited as a paraphrase, link was displayed, user never clicked, ads were shown alongside.

## Event type reference

Seven event types. The first five track content through the attribution funnel. The last two bracket conversation turns.

### `content_retrieved`

Content fetched over HTTP. The only stage content owners can observe today (via server logs or CDN). Multiple observers (edge, origin, agent) can report the same retrieval - the `content_telemetry_id` header correlates them.

| Field | Type | Description |
|-------|------|-------------|
| `source_role` | string | Who reported: `origin`, `edge`, `index`, `agent` |
| `content_telemetry_id` | uuid | Correlation ID from the `Content-Telemetry-ID` HTTP header |
| `content_url` | uri | URL as fetched |
| `content_id` | string | Stable content identifier (CMS ID, DOI, ISBN) |
| `data.media_type` | string | `text`, `image`, `video`, `audio` |
| `data.user_agent` | string | Request User-Agent header (edge/origin) |
| `data.bot_category` | string | `training`, `inference`, `search` (edge) |
| `data.bot_name` | string | Recognised bot family parsed from the UA, e.g. `Claude-User` (edge) |
| `data.verified` | boolean | Bot identity cryptographically verified (edge) |
| `data.cache_status` | string | `hit`, `miss`, `bypass`, `dynamic` (edge) |
| `data.response_status` | integer | HTTP response status code |
| `data.response_bytes` | integer | Response body size in bytes (edge) |
| `data.ja4` | string | JA4 TLS client fingerprint (edge) |
| `data.asn` | integer | Client AS number (edge) |
| `data.asn_org` | string | Client AS organisation name (edge) |
| `data.country` | string | ISO 3166-1 alpha-2 country code (edge) |
| `data.ip_hash` | string | SHA-256 of client IP (edge/origin) |

### `content_grounded`

Content loaded into the generation model's context. This is the boundary where content can directly influence the response. Cached content that was fetched days ago still produces a grounding event in every session it influences.

| Field | Type | Description |
|-------|------|-------------|
| `content_url` | uri | Content URL |
| `content_id` | string | Stable content identifier |
| `data.scope` | string | `session` (all subsequent turns) or `turn` (this turn only) |
| `data.cached` | boolean | Served from agent-side cache, not a live fetch |
| `data.tokens_ingested` | integer | Tokens placed in generation context |
| `data.content_version` | string | ETag, revision ID, or CMS version |
| `data.content_last_modified` | datetime | When source content was last modified |
| `data.content_hash` | string | SHA-256 of content as ingested (`sha256:{hex}`) |
| `data.media_type` | string | `text`, `image`, `video`, `audio` |

### `content_cited`

Content explicitly referenced in the agent's response.

| Field | Type | Description |
|-------|------|-------------|
| `content_url` | uri | Cited content URL |
| `content_id` | string | Stable content identifier |
| `data.citation_type` | string | `direct_quote`, `paraphrase`, `reference`, `contradiction`, `unclassified` |
| `data.position` | string | Prominence: `primary`, `supporting`, `mentioned`, `unclassified` |
| `data.excerpt_tokens` | integer | Token count of excerpt used |
| `data.excerpt_chars` | integer | Character count of excerpt used |
| `data.media_type` | string | `text`, `image`, `video`, `audio` |
| `data.content_hash` | string | SHA-256 matching the grounding event |
| `data.url_verified` | boolean | Agent confirmed URL resolves to matching content |

### `content_displayed`

User saw the content reference in the response.

| Field | Type | Description |
|-------|------|-------------|
| `content_url` | uri | Displayed content URL |
| `content_id` | string | Stable content identifier |
| `data.display_type` | string | `link`, `snippet`, `inline_quote`, `card`, `detail_view` |

### `content_engaged`

User interacted with the content reference.

| Field | Type | Description |
|-------|------|-------------|
| `content_url` | uri | Engaged content URL |
| `content_id` | string | Stable content identifier |
| `data.engagement_type` | string | `link_click`, `expand`, `copy`, `share` |

### `turn_started` / `turn_completed`

Bracket a conversation turn. Carry conversation context at one of four privacy levels.

| Field | Type | Description |
|-------|------|-------------|
| `turn_id` | string | Turn identifier, scoped to the session |
| `turn.privacy_level` | string | `full`, `summary`, `intent`, `minimal` |
| `turn.query_text` | string | User query (full/summary only) |
| `turn.response_text` | string | Agent response (full/summary only) |
| `turn.query_intent` | string | Classified intent: `question`, `comparison`, `how_to`, `purchase_intent`, etc. |
| `turn.response_mode` | string | `standard`, `deep_research`, `search`, `code_generation` |
| `turn.topics` | array | Detected topics/entities |
| `turn.query_tokens` | integer | Query token count |
| `turn.response_tokens` | integer | Response token count |
| `turn.model_id` | string | Model identifier (e.g. `claude-4-sonnet`) |
| `turn.ad_rendered` | boolean | Whether ads were shown alongside the response |

## What the data looks like

The spec defines a signal format, not a wire protocol - transport is left to implementers (HTTP postback, bulk upload, message queue, direct write). There are two delivery formats: the session document shown above (a complete session with nested events, validated by [telemetry-session.json](./telemetry-session.json)) and the standalone event envelope (one event plus a session reference, delivered as it occurs, validated by [telemetry-event.json](./telemetry-event.json)). Both carry the same event shapes; see [section 7.1](./SPECIFICATION.md#71-delivery-formats).

What consumers actually care about is a flat view they can query, export, or pipe into a dashboard. Here's what the same session from the quick example above looks like flattened.

### Flat event log

Each event becomes one row. Common fields (`session_id`, `agent_id`, `timestamp`, `type`) are the same across all rows; type-specific fields fill their columns and the rest are null.

```
session_id                            | agent_id   | timestamp            | type              | turn_id | content_url                          | content_id | source_role | citation_type | position  | display_type | engagement_type | scope   | cached | tokens_ingested | privacy_level | response_tokens | ad_rendered
--------------------------------------|------------|----------------------|-------------------|---------|--------------------------------------|------------|-------------|---------------|-----------|--------------|-----------------|---------|--------|-----------------|---------------|-----------------|------------
660e8400-e29b-41d4-a716-446655440000  | copilot-v3 | 2026-03-28T09:00:00Z | content_grounded  |         | https://www.reuters.com/article/abc123    | reuters:abc123  |             |               |           |              |                 | session | true   | 3200            |               |                 |
660e8400-e29b-41d4-a716-446655440000  | copilot-v3 | 2026-03-28T09:00:01Z | turn_started      | 1       |                                      |            |             |               |           |              |                 |         |        |                 | intent        |                 |
660e8400-e29b-41d4-a716-446655440000  | copilot-v3 | 2026-03-28T09:00:05Z | content_cited     | 1       | https://www.reuters.com/article/abc123    | reuters:abc123  |             | paraphrase    | primary   |              |                 |         |        |                 |               |                 |
660e8400-e29b-41d4-a716-446655440000  | copilot-v3 | 2026-03-28T09:00:05Z | content_displayed | 1       | https://www.reuters.com/article/abc123    | reuters:abc123  |             |               |           | link         |                 |         |        |                 |               |                 |
660e8400-e29b-41d4-a716-446655440000  | copilot-v3 | 2026-03-28T09:00:05Z | turn_completed    | 1       |                                      |            |             |               |           |              |                 |         |        |                 | intent        | 280             | true
```

### CSV export

The same data in CSV - what you'd export for a spreadsheet or BI tool:

```csv
session_id,agent_id,timestamp,type,turn_id,content_url,content_id,source_role,citation_type,position,display_type,engagement_type,scope,cached,tokens_ingested,privacy_level,response_tokens,ad_rendered
660e8400-e29b-41d4-a716-446655440000,copilot-v3,2026-03-28T09:00:00Z,content_grounded,,https://www.reuters.com/article/abc123,reuters:abc123,,,,,session,true,3200,,,
660e8400-e29b-41d4-a716-446655440000,copilot-v3,2026-03-28T09:00:01Z,turn_started,1,,,,,,,,,,,intent,,
660e8400-e29b-41d4-a716-446655440000,copilot-v3,2026-03-28T09:00:05Z,content_cited,1,https://www.reuters.com/article/abc123,reuters:abc123,,paraphrase,primary,,,,,,,,
660e8400-e29b-41d4-a716-446655440000,copilot-v3,2026-03-28T09:00:05Z,content_displayed,1,https://www.reuters.com/article/abc123,reuters:abc123,,,,link,,,,,,,
660e8400-e29b-41d4-a716-446655440000,copilot-v3,2026-03-28T09:00:05Z,turn_completed,1,,,,,,,,,,,intent,280,true
```

### Richer example - deep research session with clickthrough

A user asks an AI agent to compare mortgage rates. The agent does a deep research pass, retrieves three sources, grounds two, cites both, and the user clicks through to one.

```csv
session_id,agent_id,timestamp,type,turn_id,content_url,content_id,source_role,citation_type,position,display_type,engagement_type,scope,cached,tokens_ingested,privacy_level,response_tokens,ad_rendered
aa1e8400-e29b-41d4-a716-446655440000,search-agent,2026-03-28T14:00:00Z,content_retrieved,,https://www.bankofengland.co.uk/monetary-policy/12345,boe:12345,agent,,,,,,false,,,,
aa1e8400-e29b-41d4-a716-446655440000,search-agent,2026-03-28T14:00:00Z,content_retrieved,,https://www.reuters.com/markets/def456,reuters:def456,agent,,,,,,false,,,,
aa1e8400-e29b-41d4-a716-446655440000,search-agent,2026-03-28T14:00:00Z,content_retrieved,,https://www.bloomberg.com/news/ghi789,bloomberg:ghi789,agent,,,,,,false,,,,
aa1e8400-e29b-41d4-a716-446655440000,search-agent,2026-03-28T14:00:01Z,content_grounded,,https://www.bankofengland.co.uk/monetary-policy/12345,boe:12345,,,,,turn,false,2100,,,
aa1e8400-e29b-41d4-a716-446655440000,search-agent,2026-03-28T14:00:01Z,content_grounded,,https://www.reuters.com/markets/def456,reuters:def456,,,,,turn,false,4500,,,
aa1e8400-e29b-41d4-a716-446655440000,search-agent,2026-03-28T14:00:01Z,turn_started,1,,,,,,,,,,,,intent,,
aa1e8400-e29b-41d4-a716-446655440000,search-agent,2026-03-28T14:00:10Z,content_cited,1,https://www.reuters.com/markets/def456,reuters:def456,,direct_quote,primary,,,,,,,,
aa1e8400-e29b-41d4-a716-446655440000,search-agent,2026-03-28T14:00:10Z,content_cited,1,https://www.bankofengland.co.uk/monetary-policy/12345,boe:12345,,paraphrase,supporting,,,,,,,,
aa1e8400-e29b-41d4-a716-446655440000,search-agent,2026-03-28T14:00:10Z,content_displayed,1,https://www.reuters.com/markets/def456,reuters:def456,,,,card,,,,,,,
aa1e8400-e29b-41d4-a716-446655440000,search-agent,2026-03-28T14:00:10Z,content_displayed,1,https://www.bankofengland.co.uk/monetary-policy/12345,boe:12345,,,,link,,,,,,,
aa1e8400-e29b-41d4-a716-446655440000,search-agent,2026-03-28T14:00:10Z,turn_completed,1,,,,,,,,,,,,intent,850,true
aa1e8400-e29b-41d4-a716-446655440000,search-agent,2026-03-28T14:00:15Z,content_engaged,1,https://www.reuters.com/markets/def456,reuters:def456,,,,,,link_click,,,,,,
```

What a content owner can read from this:

- Three sources retrieved, but the Bloomberg article (`ghi789`) was never grounded - fetched but not used
- Reuters article was the primary source (direct quote, shown as a card), Bank of England page was supporting (paraphrase, shown as a link)
- User clicked through to the Reuters article but not the Bank of England one
- 850 response tokens, ads were shown, privacy level is `intent` (no query/response text shared)

## Relationship to other protocols

OpenAttribution Telemetry is the **reporting** side. Content **access** protocols (peek-then-pay, IAB CoMP, bilateral APIs) govern how agents discover and license content. The `license_ref` field on events connects telemetry to whatever access protocol issued the licence. The schemas are independent - telemetry works with any access protocol, or none.

## Implementations

| Language | Package | Status | Source |
|----------|---------|--------|--------|
| TypeScript / JavaScript | [`@openattribution/telemetry`](https://www.npmjs.com/package/@openattribution/telemetry) | Published on npm | [openattribution-org/telemetry-js](https://github.com/openattribution-org/telemetry-js) |
| Python | `openattribution-telemetry` | In progress, not yet on PyPI | [openattribution-org/telemetry-py](https://github.com/openattribution-org/telemetry-py) |

SDK repos have their own release cadences and declare which spec version they support. Where no SDK exists yet, the schemas in this repo are the reference - any JSON Schema draft 2020-12 validator can check session documents, standalone events, and manifests against them (see "Validating an implementation" below). Implementations in other languages are welcome - open an issue if you're building one.

## Open questions in v0.1

This is a preview specification. Two areas are under active discussion and will be refined with implementer input:

**Grounding boundary.** The spec defines grounding as content entering the generation model's context (section 4.2, 6.4). For straightforward RAG pipelines this is clear. For pipelines with multiple processing stages - embedding, re-ranking, summarisation before context insertion - the boundary requires judgement. The spec draws the line at the generation context (not earlier retrieval stages), but edge cases remain. See [CONSIDERATIONS.md](./CONSIDERATIONS.md#grounding-boundary-definition) for the full discussion. Input from platform engineering teams building real implementations will sharpen this definition.

**Event volume at scale.** A single deep-research query can produce 100+ retrieval events and dozens of grounding/citation events. The session document format already handles transport - one POST with all events after the session ends, not one request per event. Volume management beyond that (storage, processing, consumer-side aggregation) is an implementation concern, not a protocol gap. Sampling and aggregation are options for future versions but are deliberately not in v0.1 - what gets reported and at what granularity is a commercial decision between the parties, not a protocol default. See [CONSIDERATIONS.md](./CONSIDERATIONS.md#event-volume-and-scale-guidance) for options under consideration.

## Versioning

This repo tracks the specification version. SDK repos have their own release cadences and declare which spec version they support.

Current spec version: **0.1** (preview)

## Validating an implementation

The repo ships a conformance test suite in [tests/](./tests/) - valid and invalid fixtures plus a runner:

```sh
pip install jsonschema
python tests/validate.py
```

(`uvx --from jsonschema python tests/validate.py` or `uv pip install jsonschema` work too if you prefer `uv`.)

Exit code 0 means every fixture behaved as expected: each file under `tests/valid/` validated, each file under `tests/invalid/` was rejected. The runner checks two things - JSON Schema validity against [telemetry-session.json](./telemetry-session.json), [telemetry-event.json](./telemetry-event.json), and [manifest.json](./manifest.json), and the application-layer rules that JSON Schema cannot express (privacy-level field gating - for example `query_text` MUST NOT appear on a turn at `minimal` or `intent` privacy). To check your own session documents, events, or manifests, validate them against the relevant schema with any JSON Schema draft 2020-12 validator.

## Get involved

- **Feedback** via [GitHub Issues](https://github.com/openattribution-org/telemetry/issues)
- **Implementations** in other languages welcome
- **Use cases** we haven't considered

Visit [openattribution.org](https://openattribution.org) for more information.

## Licence

Apache 2.0 - see [LICENSE](./LICENSE) for details.
