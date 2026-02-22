/**
 * OpenAttribution Telemetry — HTTP client.
 *
 * Zero dependencies — uses native fetch (Node 18+, Deno, browsers, Edge).
 */

import type {
  ConversationTurn,
  EventType,
  Initiator,
  SessionOutcome,
  StartSessionOptions,
  TelemetryClientOptions,
  TelemetryEvent,
  TelemetrySession,
  UserContext,
} from "./types.js";

const TRANSIENT_STATUS_CODES = new Set([429, 500, 502, 503, 504]);

// ---------------------------------------------------------------------------
// Wire format helpers (camelCase → snake_case for the JSON body)
// ---------------------------------------------------------------------------

function turnToWire(turn: ConversationTurn): Record<string, unknown> {
  return {
    privacy_level: turn.privacyLevel,
    query_text: turn.queryText,
    response_text: turn.responseText,
    query_intent: turn.queryIntent,
    response_type: turn.responseType,
    topics: turn.topics,
    content_urls_retrieved: turn.contentUrlsRetrieved,
    content_urls_cited: turn.contentUrlsCited,
    query_tokens: turn.queryTokens,
    response_tokens: turn.responseTokens,
    model_id: turn.modelId,
  };
}

function eventToWire(event: TelemetryEvent): Record<string, unknown> {
  return {
    id: event.id,
    type: event.type,
    timestamp: event.timestamp,
    content_url: event.contentUrl,
    product_id: event.productId,
    turn: event.turn != null ? turnToWire(event.turn) : undefined,
    data: event.data ?? {},
  };
}

function initiatorToWire(i: Initiator): Record<string, unknown> {
  return {
    agent_id: i.agentId,
    manifest_ref: i.manifestRef,
    operator_id: i.operatorId,
  };
}

function userContextToWire(uc: UserContext): Record<string, unknown> {
  return {
    external_id: uc.externalId,
    segments: uc.segments ?? [],
    attributes: uc.attributes ?? {},
  };
}

function outcomeToWire(o: SessionOutcome): Record<string, unknown> {
  return {
    type: o.type,
    value_amount: o.valueAmount ?? 0,
    currency: o.currency ?? "USD",
    products: o.products ?? [],
    metadata: o.metadata ?? {},
  };
}

// ---------------------------------------------------------------------------
// TelemetryClient
// ---------------------------------------------------------------------------

/**
 * Async client for recording OpenAttribution telemetry.
 *
 * Works in Node.js ≥ 18, Deno, browsers, and Edge runtimes (Vercel, Cloudflare).
 *
 * @example
 * ```ts
 * const client = new TelemetryClient({
 *   endpoint: "https://telemetry.example.com",
 *   apiKey: "your-api-key",
 *   failSilently: true,
 * });
 *
 * const sessionId = await client.startSession({ contentScope: "my-mix" });
 *
 * await client.recordEvents(sessionId, [
 *   { id: crypto.randomUUID(), type: "content_retrieved",
 *     timestamp: new Date().toISOString(), contentUrl: "https://..." }
 * ]);
 *
 * await client.endSession(sessionId, { type: "browse" });
 * ```
 */
export class TelemetryClient {
  private readonly endpoint: string;
  private readonly apiKey: string | undefined;
  private readonly failSilently: boolean;
  private readonly timeout: number;
  private readonly maxRetries: number;

  constructor(options: TelemetryClientOptions) {
    this.endpoint = options.endpoint.replace(/\/$/, "");
    this.apiKey = options.apiKey;
    this.failSilently = options.failSilently ?? true;
    this.timeout = options.timeout ?? 30_000;
    this.maxRetries = options.maxRetries ?? 3;
  }

  private headers(): Record<string, string> {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (this.apiKey != null) h["X-API-Key"] = this.apiKey;
    return h;
  }

  private async post(path: string, body: unknown): Promise<unknown> {
    const url = `${this.endpoint}${path}`;
    let lastError: unknown;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), this.timeout);

      try {
        const res = await fetch(url, {
          method: "POST",
          headers: this.headers(),
          body: JSON.stringify(body),
          signal: controller.signal,
        });

        if (TRANSIENT_STATUS_CODES.has(res.status) && attempt < this.maxRetries) {
          const wait = 2 ** attempt * 1000 + Math.random() * 500;
          await sleep(wait);
          continue;
        }

        if (!res.ok) {
          throw new Error(`HTTP ${res.status} ${res.statusText} from ${url}`);
        }

        return await res.json();
      } catch (err) {
        lastError = err;
        if (attempt < this.maxRetries && isTransientError(err)) {
          const wait = 2 ** attempt * 1000 + Math.random() * 500;
          await sleep(wait);
        } else {
          break;
        }
      } finally {
        clearTimeout(timer);
      }
    }

    if (this.failSilently) {
      return null;
    }
    throw lastError;
  }

  /**
   * Start a new telemetry session.
   *
   * @returns Session ID string, or null on silent failure.
   */
  async startSession(options: StartSessionOptions = {}): Promise<string | null> {
    const result = await this.post("/session/start", {
      initiator_type: options.initiatorType ?? "user",
      initiator:
        options.initiator != null ? initiatorToWire(options.initiator) : null,
      content_scope: options.contentScope,
      agent_id: options.agentId,
      external_session_id: options.externalSessionId,
      user_context:
        options.userContext != null
          ? userContextToWire(options.userContext)
          : {},
      manifest_ref: options.manifestRef,
      prior_session_ids: options.priorSessionIds ?? [],
    }) as { session_id?: string } | null;

    return result?.session_id ?? null;
  }

  /**
   * Record a single telemetry event.
   */
  async recordEvent(
    sessionId: string | null,
    eventType: EventType,
    options: {
      contentUrl?: string;
      productId?: string;
      turn?: ConversationTurn;
      data?: Record<string, unknown>;
    } = {},
  ): Promise<void> {
    if (sessionId == null) return;
    await this.recordEvents(sessionId, [
      {
        id: crypto.randomUUID(),
        type: eventType,
        timestamp: new Date().toISOString(),
        ...options,
      },
    ]);
  }

  /**
   * Record a batch of telemetry events.
   */
  async recordEvents(
    sessionId: string | null,
    events: TelemetryEvent[],
  ): Promise<void> {
    if (sessionId == null || events.length === 0) return;
    await this.post("/events", {
      session_id: sessionId,
      events: events.map(eventToWire),
    });
  }

  /**
   * End a session with an outcome.
   */
  async endSession(
    sessionId: string | null,
    outcome: SessionOutcome,
  ): Promise<void> {
    if (sessionId == null) return;
    await this.post("/session/end", {
      session_id: sessionId,
      outcome: outcomeToWire(outcome),
    });
  }

  /**
   * Upload a complete session in one request (bulk path).
   *
   * Useful for post-hoc reporting or when you've built the session
   * locally and want to submit it in one shot.
   *
   * @returns Server-assigned session ID, or null on silent failure.
   */
  async uploadSession(session: TelemetrySession): Promise<string | null> {
    const result = await this.post("/session/bulk", sessionToWire(session)) as
      | { session_id?: string }
      | null;
    return result?.session_id ?? null;
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isTransientError(err: unknown): boolean {
  if (err instanceof Error) {
    // AbortError (timeout), network errors
    return (
      err.name === "AbortError" ||
      err.name === "TypeError" ||
      err.message.includes("fetch")
    );
  }
  return false;
}

function sessionToWire(session: TelemetrySession): Record<string, unknown> {
  return {
    schema_version: session.schemaVersion ?? "0.4",
    session_id: session.sessionId,
    initiator_type: session.initiatorType ?? "user",
    initiator:
      session.initiator != null ? initiatorToWire(session.initiator) : null,
    agent_id: session.agentId,
    content_scope: session.contentScope,
    manifest_ref: session.manifestRef,
    prior_session_ids: session.priorSessionIds ?? [],
    started_at: session.startedAt,
    ended_at: session.endedAt,
    user_context:
      session.userContext != null
        ? userContextToWire(session.userContext)
        : {},
    events: session.events.map(eventToWire),
    outcome:
      session.outcome != null ? outcomeToWire(session.outcome) : undefined,
  };
}
