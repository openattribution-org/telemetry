/**
 * OpenAttribution Telemetry — ACP (Agentic Commerce Protocol) bridge.
 *
 * Converts a TelemetrySession into the `content_attribution` object
 * defined in the ACP RFC. Include this in a CheckoutSessionCreateRequest
 * or CheckoutSessionCompleteRequest.
 *
 * Reference: acp/rfc.content_attribution.md
 */

import type { TelemetrySession } from "./types.js";

export interface ContentAttributionRetrieved {
  content_url: string;
  timestamp: string;
}

export interface ContentAttributionCited {
  content_url: string;
  timestamp: string;
  citation_type?: string;
  excerpt_tokens?: number;
  position?: string;
  content_hash?: string;
}

export interface ConversationSummary {
  turn_count: number;
  topics: string[];
}

/**
 * ACP `content_attribution` object.
 * Include in CheckoutSessionCreateRequest.content_attribution.
 */
export interface ContentAttribution {
  content_scope?: string;
  content_retrieved: ContentAttributionRetrieved[];
  content_cited?: ContentAttributionCited[];
  conversation_summary?: ConversationSummary;
}

/**
 * Convert a TelemetrySession into an ACP `content_attribution` object.
 *
 * @example
 * ```ts
 * import { sessionToContentAttribution } from "@openattribution/telemetry/acp";
 *
 * const attribution = sessionToContentAttribution(session);
 *
 * // Include in ACP checkout request:
 * await acp.createCheckout({
 *   cart: { ... },
 *   content_attribution: attribution,
 * });
 * ```
 */
export function sessionToContentAttribution(
  session: TelemetrySession,
): ContentAttribution {
  const retrieved: ContentAttributionRetrieved[] = session.events
    .filter((e) => e.type === "content_retrieved" && e.contentUrl != null)
    .map((e) => ({
      content_url: e.contentUrl!,
      timestamp: e.timestamp,
    }));

  const cited: ContentAttributionCited[] = session.events
    .filter((e) => e.type === "content_cited" && e.contentUrl != null)
    .map((e) => ({
      content_url: e.contentUrl!,
      timestamp: e.timestamp,
      ...(e.data?.["citation_type"] != null && {
        citation_type: String(e.data["citation_type"]),
      }),
      ...(e.data?.["excerpt_tokens"] != null && {
        excerpt_tokens: Number(e.data["excerpt_tokens"]),
      }),
      ...(e.data?.["position"] != null && {
        position: String(e.data["position"]),
      }),
      ...(e.data?.["content_hash"] != null && {
        content_hash: String(e.data["content_hash"]),
      }),
    }));

  const turnEvents = session.events.filter(
    (e) => e.type === "turn_completed" || e.type === "turn_started",
  );
  const turnCount = Math.max(
    session.events.filter((e) => e.type === "turn_completed").length,
    1,
  );

  const topics = [
    ...new Set(
      session.events.flatMap((e) => e.turn?.topics ?? []),
    ),
  ];

  const result: ContentAttribution = {
    ...(session.contentScope != null && { content_scope: session.contentScope }),
    content_retrieved: retrieved,
    ...(cited.length > 0 && { content_cited: cited }),
    ...((turnEvents.length > 0 || topics.length > 0) && {
      conversation_summary: { turn_count: turnCount, topics },
    }),
  };

  return result;
}
