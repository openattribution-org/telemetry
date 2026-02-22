# @openattribution/telemetry

TypeScript/JavaScript SDK for [OpenAttribution Telemetry](https://openattribution.org/telemetry) — track content attribution in AI agent interactions.

Works in Node.js ≥ 18, Deno, browsers, and Edge runtimes (Vercel, Cloudflare Workers). Zero runtime dependencies.

## Install

```bash
npm install @openattribution/telemetry
# or
pnpm add @openattribution/telemetry
# or
yarn add @openattribution/telemetry
```

## Quick start

```ts
import { TelemetryClient } from "@openattribution/telemetry";

const client = new TelemetryClient({
  endpoint: "https://your-telemetry-server.com",
  apiKey: process.env.TELEMETRY_API_KEY,
  failSilently: true, // recommended — never let telemetry break your app
});

const sessionId = await client.startSession({
  contentScope: "my-agent",
  externalSessionId: "conv-abc123", // link to your own session/conversation ID
});

await client.recordEvents(sessionId, [
  {
    id: crypto.randomUUID(),
    type: "content_retrieved",
    timestamp: new Date().toISOString(),
    contentUrl: "https://wirecutter.com/reviews/best-headphones",
  },
  {
    id: crypto.randomUUID(),
    type: "content_cited",
    timestamp: new Date().toISOString(),
    contentUrl: "https://wirecutter.com/reviews/best-headphones",
    data: { citation_type: "paraphrase", position: "primary" },
  },
]);

await client.endSession(sessionId, { type: "browse" });
```

## MCP agents

MCP tool calls are stateless — each invocation is independent. `MCPSessionTracker` solves this by maintaining an in-process session registry keyed on a caller-supplied `session_id` string, so multiple tool calls in the same conversation chain into one telemetry session.

```ts
import { TelemetryClient, MCPSessionTracker, extractResultUrls } from "@openattribution/telemetry";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

const client = new TelemetryClient({
  endpoint: process.env.TELEMETRY_ENDPOINT!,
  apiKey: process.env.TELEMETRY_API_KEY,
  failSilently: true,
});

const tracker = new MCPSessionTracker(client, "my-shopping-agent");

const server = new McpServer({ name: "my-agent", version: "1.0.0" });

server.tool(
  "search_products",
  {
    query: z.string().describe("What to search for"),
    sessionId: z.string().optional().describe(
      "Pass a stable conversation ID to link tool calls into one session"
    ),
  },
  async ({ query, sessionId }) => {
    const products = await myProductSearch(query);

    // Fire telemetry in background — never blocks the tool response
    void tracker.trackRetrieved(sessionId, extractResultUrls(products));

    return { content: [{ type: "text", text: formatProducts(products) }] };
  }
);
```

The `session_id` param is optional — agents that don't pass one get per-call anonymous sessions. Agents that pass a stable conversation ID get full session continuity across `search_products`, `compare_prices`, and `find_deals` calls.

## Next.js / Vercel AI SDK

Track web search citations from AI responses. The `:online` suffix on OpenRouter models (and similar web-search-enabled models) injects citation links as Markdown into the response text. `extractCitationUrls` pulls them out.

```ts
// app/api/chat/route.ts
import { streamText } from "ai";
import { TelemetryClient, MCPSessionTracker, extractCitationUrls } from "@openattribution/telemetry";

const client = new TelemetryClient({
  endpoint: process.env.TELEMETRY_ENDPOINT!,
  apiKey: process.env.TELEMETRY_API_KEY,
  failSilently: true,
});
const tracker = new MCPSessionTracker(client, "my-chat-agent");

export async function POST(req: Request) {
  const { messages, sessionId } = await req.json();

  const result = streamText({
    model: openrouter("openai/gpt-4.1-nano:online"),
    messages,
    onFinish: async ({ text }) => {
      // Extract citation URLs from the completed response
      const citedUrls = extractCitationUrls(text);
      if (citedUrls.length > 0) {
        void tracker.trackCited(sessionId, citedUrls, {
          citationType: "reference",
          position: "supporting",
        });
      }
    },
  });

  return result.toDataStreamResponse();
}
```

## ACP checkout integration

When a checkout occurs, convert your telemetry session into the ACP `content_attribution` object:

```ts
import { sessionToContentAttribution } from "@openattribution/telemetry";

// Build a complete session for submission
const session = {
  sessionId: crypto.randomUUID(),
  startedAt: sessionStartTime.toISOString(),
  contentScope: "my-agent",
  events: collectedEvents,
};

const attribution = sessionToContentAttribution(session);

// Include in your ACP checkout request
await acpClient.createCheckout({
  cart: { ... },
  content_attribution: attribution,
});
```

## UCP checkout integration

```ts
import { sessionToAttribution } from "@openattribution/telemetry";

const attribution = sessionToAttribution(session);

await ucpClient.completeCheckout({
  order: { ... },
  extensions: {
    "org.openattribution.telemetry": attribution,
  },
});
```

## API reference

### `TelemetryClient`

| Method | Description |
|--------|-------------|
| `startSession(options?)` | Create a session. Returns session ID string or `null`. |
| `recordEvent(sessionId, type, options?)` | Record a single event. |
| `recordEvents(sessionId, events[])` | Record a batch of events. |
| `endSession(sessionId, outcome)` | End a session with outcome. |
| `uploadSession(session)` | Bulk upload a complete session in one request. |

### `MCPSessionTracker`

| Method | Description |
|--------|-------------|
| `trackRetrieved(externalId, urls[])` | Emit `content_retrieved` events. Creates session if needed. |
| `trackCited(externalId, urls[], options?)` | Emit `content_cited` events. |
| `endSession(externalId, outcome)` | End the session and remove from registry. |
| `getOrCreateSession(externalId)` | Get or create an OA session ID. |

### `extractCitationUrls(text)`

Extract HTTP/HTTPS URLs from Markdown-formatted text. Finds both `[anchor](url)` links and bare URLs. Returns deduplicated array.

### `extractResultUrls(results[])`

Extract URLs from a list of search result objects with a `url` or `link` field. Works with Channel3, Exa, Tavily, and most search APIs.

### `sessionToContentAttribution(session)`

Convert a `TelemetrySession` to an ACP `content_attribution` object. See [acp/rfc.content_attribution.md](../acp/rfc.content_attribution.md).

### `sessionToAttribution(session)`

Convert a `TelemetrySession` to a UCP attribution extension object. See [ucp/EXTENSION.md](../ucp/EXTENSION.md).

## Event types

| Type | When to emit |
|------|-------------|
| `content_retrieved` | Content fetched from any source (search results, RAG, product APIs) |
| `content_cited` | Content explicitly referenced in the agent's response |
| `turn_started` | User submitted a message |
| `turn_completed` | Agent finished responding |
| `product_viewed` | User viewed a product detail |
| `product_compared` | Agent compared multiple products |
| `cart_add` | Item added to cart |
| `checkout_started` | Checkout flow initiated |
| `checkout_completed` | Purchase completed |

## Privacy levels

`ConversationTurn` supports four privacy levels controlling what conversation data is shared:

| Level | What's included |
|-------|----------------|
| `minimal` | Token counts, content URLs only (default, always safe) |
| `intent` | Classified intent category and topics, no raw text |
| `summary` | LLM-generated summary |
| `full` | Complete query and response text |

## Reference server

A reference FastAPI server implementation is in [`../server/`](../server/). Run it locally with:

```bash
cd server
pip install -e ".[dev]"
uvicorn openattribution.telemetry_server.main:app --reload
```

## Licence

Apache 2.0 — see [LICENSE](../LICENSE).
