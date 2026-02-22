/**
 * OpenAttribution Telemetry — MCP session tracker.
 *
 * Provides session continuity across stateless MCP tool calls.
 * The calling agent passes a stable `sessionId` string; this module
 * maps it to an OA session UUID and reuses it across tool calls within
 * the same server process.
 *
 * Usage in an MCP tool:
 *
 * ```ts
 * import { TelemetryClient, MCPSessionTracker } from "@openattribution/telemetry";
 *
 * const client = new TelemetryClient({ endpoint: "...", apiKey: "..." });
 * const tracker = new MCPSessionTracker(client, "my-agent");
 *
 * // In your MCP tool handler:
 * server.tool("search_products", { query: z.string(), sessionId: z.string().optional() },
 *   async ({ query, sessionId }) => {
 *     const results = await searchProducts(query);
 *     await tracker.trackRetrieved(sessionId, results.map(r => r.url));
 *     return formatResults(results);
 *   }
 * );
 * ```
 */

import type { TelemetryEvent } from "./types.js";
import type { TelemetryClient } from "./client.js";

/**
 * Session tracker for MCP agents.
 *
 * Maintains an in-process mapping of external session IDs to OA session UUIDs.
 * Sessions are created on first use and reused across subsequent tool calls.
 *
 * The in-process registry is intentionally simple — it works correctly for
 * single-process MCP servers. For distributed deployments, pass a shared
 * external store to the constructor.
 */
export class MCPSessionTracker {
  private readonly client: TelemetryClient;
  private readonly contentScope: string;
  private readonly registry = new Map<string, string | null>();

  /**
   * @param client - Configured TelemetryClient instance.
   * @param contentScope - Stable identifier for this agent's content scope
   *   (e.g. mix ID, manifest reference, or descriptive slug like "my-shopping-agent").
   */
  constructor(client: TelemetryClient, contentScope = "mcp-agent") {
    this.client = client;
    this.contentScope = contentScope;
  }

  /**
   * Get or create an OA session for the given external session ID.
   *
   * If `externalSessionId` is undefined, a new anonymous session is created
   * on every call (no continuity across tool calls).
   *
   * @returns OA session ID string, or null on silent failure.
   */
  async getOrCreateSession(
    externalSessionId: string | undefined,
  ): Promise<string | null> {
    if (externalSessionId != null && this.registry.has(externalSessionId)) {
      return this.registry.get(externalSessionId) ?? null;
    }

    const sessionId = await this.client.startSession({
      contentScope: this.contentScope,
      ...(externalSessionId != null && { externalSessionId }),
    });

    if (externalSessionId != null) {
      this.registry.set(externalSessionId, sessionId);
    }

    return sessionId;
  }

  /**
   * Emit `content_retrieved` events for a list of URLs.
   *
   * Call this after fetching products, search results, or any content
   * that influenced the agent's response.
   *
   * @param externalSessionId - Caller-supplied conversation identifier.
   * @param urls - URLs of content retrieved during this tool call.
   */
  async trackRetrieved(
    externalSessionId: string | undefined,
    urls: string[],
  ): Promise<void> {
    if (urls.length === 0) return;
    const sessionId = await this.getOrCreateSession(externalSessionId);
    if (sessionId == null) return;

    const now = new Date().toISOString();
    const events: TelemetryEvent[] = urls.map((url) => ({
      id: crypto.randomUUID(),
      type: "content_retrieved" as const,
      timestamp: now,
      contentUrl: url,
    }));

    await this.client.recordEvents(sessionId, events);
  }

  /**
   * Emit `content_cited` events for content explicitly referenced in a response.
   *
   * Call this when you know which content the agent cited — e.g. the top
   * search result, an editorial quote, or a product recommendation.
   *
   * @param externalSessionId - Caller-supplied conversation identifier.
   * @param urls - URLs of content cited in the agent's response.
   * @param options - Optional citation metadata.
   */
  async trackCited(
    externalSessionId: string | undefined,
    urls: string[],
    options: {
      citationType?: "direct_quote" | "paraphrase" | "reference" | "contradiction";
      position?: "primary" | "supporting" | "mentioned";
    } = {},
  ): Promise<void> {
    if (urls.length === 0) return;
    const sessionId = await this.getOrCreateSession(externalSessionId);
    if (sessionId == null) return;

    const now = new Date().toISOString();
    const events: TelemetryEvent[] = urls.map((url) => ({
      id: crypto.randomUUID(),
      type: "content_cited" as const,
      timestamp: now,
      contentUrl: url,
      data: {
        ...(options.citationType != null && { citation_type: options.citationType }),
        ...(options.position != null && { position: options.position }),
      },
    }));

    await this.client.recordEvents(sessionId, events);
  }

  /**
   * End a session with an outcome.
   *
   * Call this when the conversation concludes — at checkout, after
   * the user clicks a link, or when the session times out.
   */
  async endSession(
    externalSessionId: string | undefined,
    outcome: { type: "conversion" | "abandonment" | "browse"; valueAmount?: number; currency?: string },
  ): Promise<void> {
    const sessionId = externalSessionId != null
      ? (this.registry.get(externalSessionId) ?? null)
      : null;

    if (sessionId == null) return;

    await this.client.endSession(sessionId, {
      type: outcome.type,
      ...(outcome.valueAmount != null && { valueAmount: outcome.valueAmount }),
      ...(outcome.currency != null && { currency: outcome.currency }),
    });

    this.registry.delete(externalSessionId!);
  }

  /** Number of active sessions in the registry. */
  get sessionCount(): number {
    return this.registry.size;
  }
}
