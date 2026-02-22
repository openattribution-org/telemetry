/**
 * OpenAttribution Telemetry — content URL extraction utilities.
 *
 * Helpers for extracting content URLs from AI-generated text, so they
 * can be recorded as telemetry events without manual instrumentation.
 */

/** Matches `[text](url)` — standard Markdown links. */
const MARKDOWN_LINK_RE = /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g;

/** Matches bare URLs starting with http/https. */
const BARE_URL_RE = /https?:\/\/[^\s<>"')\]]+/g;

/**
 * Extract all HTTP/HTTPS URLs from Markdown-formatted text.
 *
 * Finds URLs in two forms:
 * - Markdown links: `[anchor text](https://...)`
 * - Bare URLs: `https://...`
 *
 * Results are deduplicated. Useful for extracting citation URLs from
 * AI model responses that include web search results.
 *
 * @example
 * ```ts
 * const text = "According to [Wirecutter](https://nytimes.com/wirecutter/reviews/...), ...";
 * const urls = extractCitationUrls(text);
 * // ["https://nytimes.com/wirecutter/reviews/..."]
 * ```
 */
export function extractCitationUrls(text: string): string[] {
  const urls = new Set<string>();

  for (const match of text.matchAll(MARKDOWN_LINK_RE)) {
    const url = match[2];
    if (url != null) urls.add(cleanUrl(url));
  }

  // Only look for bare URLs if Markdown links didn't cover everything
  for (const match of text.matchAll(BARE_URL_RE)) {
    urls.add(cleanUrl(match[0]));
  }

  return [...urls];
}

/**
 * Extract URLs from a list of search result objects.
 *
 * Accepts any object with a `url` string property — works with
 * Channel3, Exa, Tavily, and most search API responses.
 *
 * @example
 * ```ts
 * const products = await channel3.search({ query: "headphones" });
 * const urls = extractResultUrls(products);
 * await tracker.trackRetrieved(sessionId, urls);
 * ```
 */
export function extractResultUrls(
  results: Array<{ url?: string | null; link?: string | null }>,
): string[] {
  const urls: string[] = [];
  for (const r of results) {
    const url = r.url ?? r.link;
    if (url != null && url.startsWith("http")) {
      urls.push(url);
    }
  }
  return [...new Set(urls)];
}

/**
 * Build a tracking URL that routes through your server-side redirect endpoint.
 *
 * Your endpoint emits a `content_engaged` event then redirects the user to
 * the original URL. This is the most reliable pattern for click tracking —
 * it fires server-side before the redirect, so it works regardless of
 * browser JS state or navigation timing.
 *
 * @param contentUrl - The destination URL to redirect to after tracking.
 * @param options.endpoint - Your tracking endpoint base URL (e.g. `https://example.com/api/track`).
 * @param options.sessionId - Optional session ID to link the click to an existing session.
 *
 * @example
 * ```ts
 * // Build a tracked URL for a product link
 * const trackedUrl = createTrackingUrl("https://shop.example.com/product", {
 *   endpoint: "https://myagent.com/api/track",
 *   sessionId: "conv-abc123",
 * });
 * // → "https://myagent.com/api/track?url=https%3A%2F%2Fshop.example.com%2Fproduct&session_id=conv-abc123"
 *
 * // Server-side handler (Next.js example):
 * export async function GET(req: Request) {
 *   const { searchParams } = new URL(req.url);
 *   const url = searchParams.get("url");
 *   const sessionId = searchParams.get("session_id") ?? undefined;
 *   if (!url) return new Response("Missing url", { status: 400 });
 *   void tracker.trackEngaged(sessionId, [url], { interactionType: "click" });
 *   return Response.redirect(url, 302);
 * }
 * ```
 */
export function createTrackingUrl(
  contentUrl: string,
  options: {
    endpoint: string;
    sessionId?: string;
  },
): string {
  const url = new URL(options.endpoint);
  url.searchParams.set("url", contentUrl);
  if (options.sessionId != null) {
    url.searchParams.set("session_id", options.sessionId);
  }
  return url.toString();
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/** Remove trailing punctuation that commonly attaches to bare URLs. */
function cleanUrl(url: string): string {
  return url.replace(/[.,;:!?]+$/, "");
}
