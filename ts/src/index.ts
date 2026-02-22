/**
 * @openattribution/telemetry
 *
 * OpenAttribution Telemetry SDK for TypeScript/JavaScript.
 * Track content attribution in AI agent interactions.
 *
 * Specification: https://openattribution.org/telemetry
 *
 * @example
 * ```ts
 * import { TelemetryClient, MCPSessionTracker, extractCitationUrls } from "@openattribution/telemetry";
 *
 * // Direct client usage
 * const client = new TelemetryClient({
 *   endpoint: "https://telemetry.example.com",
 *   apiKey: process.env.TELEMETRY_API_KEY,
 *   failSilently: true,
 * });
 *
 * // MCP agent usage
 * const tracker = new MCPSessionTracker(client, "my-shopping-agent");
 * await tracker.trackRetrieved(sessionId, productUrls);
 *
 * // Extract citation URLs from AI response text
 * const urls = extractCitationUrls(assistantMessage);
 * await tracker.trackCited(sessionId, urls);
 * ```
 */

export { TelemetryClient } from "./client.js";
export { MCPSessionTracker } from "./mcp.js";
export { extractCitationUrls, extractResultUrls } from "./extract.js";
export { sessionToContentAttribution } from "./acp.js";
export { sessionToAttribution } from "./ucp.js";

export type {
  // Types
  TelemetryClientOptions,
  TelemetrySession,
  TelemetryEvent,
  SessionOutcome,
  StartSessionOptions,
  ConversationTurn,
  UserContext,
  Initiator,
  // Enumerations
  EventType,
  OutcomeType,
  PrivacyLevel,
  IntentCategory,
  InitiatorType,
  CitationType,
  CitationPosition,
} from "./types.js";

export type { ContentAttribution, ContentAttributionRetrieved, ContentAttributionCited } from "./acp.js";
export type { UCPAttribution } from "./ucp.js";
