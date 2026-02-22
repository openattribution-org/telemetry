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

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/** Remove trailing punctuation that commonly attaches to bare URLs. */
function cleanUrl(url: string): string {
  return url.replace(/[.,;:!?]+$/, "");
}
