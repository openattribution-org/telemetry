/**
 * OpenAttribution Telemetry — UCP (Universal Checkout Protocol) bridge.
 *
 * Converts a TelemetrySession into the UCP attribution extension object.
 *
 * Reference: ucp/EXTENSION.md
 */

import type { TelemetrySession } from "./types.js";

export interface UCPAttribution {
  content_scope?: string;
  prior_session_ids?: string[];
  content_retrieved: Array<{ content_url: string; timestamp: string }>;
  content_cited?: Array<{
    content_url: string;
    timestamp: string;
    citation_type?: string;
    position?: string;
  }>;
  conversation_summary?: {
    turn_count: number;
    topics: string[];
  };
}

/**
 * Convert a TelemetrySession into a UCP attribution extension object.
 *
 * @example
 * ```ts
 * import { sessionToAttribution } from "@openattribution/telemetry/ucp";
 *
 * const attribution = sessionToAttribution(session);
 *
 * // Include in UCP checkout:
 * await ucp.completeCheckout({
 *   order: { ... },
 *   extensions: { "org.openattribution.telemetry": attribution },
 * });
 * ```
 */
export function sessionToAttribution(session: TelemetrySession): UCPAttribution {
  const retrieved = session.events
    .filter((e) => e.type === "content_retrieved" && e.contentUrl != null)
    .map((e) => ({ content_url: e.contentUrl!, timestamp: e.timestamp }));

  const cited = session.events
    .filter((e) => e.type === "content_cited" && e.contentUrl != null)
    .map((e) => ({
      content_url: e.contentUrl!,
      timestamp: e.timestamp,
      ...(e.data?.["citation_type"] != null && {
        citation_type: String(e.data["citation_type"]),
      }),
      ...(e.data?.["position"] != null && {
        position: String(e.data["position"]),
      }),
    }));

  const turnCount = Math.max(
    session.events.filter((e) => e.type === "turn_completed").length,
    1,
  );
  const topics = [...new Set(session.events.flatMap((e) => e.turn?.topics ?? []))];
  const priorIds = (session.priorSessionIds ?? []).filter(Boolean);

  return {
    ...(session.contentScope != null && { content_scope: session.contentScope }),
    ...(priorIds.length > 0 && { prior_session_ids: priorIds }),
    content_retrieved: retrieved,
    ...(cited.length > 0 && { content_cited: cited }),
    ...((topics.length > 0 || turnCount > 0) && {
      conversation_summary: { turn_count: turnCount, topics },
    }),
  };
}
