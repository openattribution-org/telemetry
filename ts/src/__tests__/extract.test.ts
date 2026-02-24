import { describe, it, expect } from "vitest"
import {
  extractCitationUrls,
  extractResultUrls,
  createTrackingUrl,
} from "../extract.js"

describe("extractCitationUrls", () => {
  it("extracts URLs from markdown links", () => {
    const text = "See [Wirecutter](https://example.com/review) for details"
    expect(extractCitationUrls(text)).toEqual(["https://example.com/review"])
  })

  it("extracts bare URLs from plain text", () => {
    const text = "Visit https://example.com today"
    expect(extractCitationUrls(text)).toEqual(["https://example.com"])
  })

  it("strips trailing punctuation from bare URLs", () => {
    const text = "Visit https://example.com."
    expect(extractCitationUrls(text)).toEqual(["https://example.com"])
  })

  it("deduplicates when the same URL appears as both a markdown link and bare URL", () => {
    const text =
      "See [Example](https://example.com/review) and also https://example.com/review"
    const result = extractCitationUrls(text)
    expect(result).toEqual(["https://example.com/review"])
    expect(result).toHaveLength(1)
  })

  it("returns empty array for empty string", () => {
    expect(extractCitationUrls("")).toEqual([])
  })
})

describe("extractResultUrls", () => {
  it("extracts URLs from objects with a url property", () => {
    const results = [{ url: "https://a.com" }, { url: "https://b.com" }]
    expect(extractResultUrls(results)).toEqual([
      "https://a.com",
      "https://b.com",
    ])
  })

  it("extracts URLs from objects with a link property", () => {
    const results = [{ link: "https://a.com" }]
    expect(extractResultUrls(results)).toEqual(["https://a.com"])
  })

  it("skips non-http URLs", () => {
    const results = [{ url: "ftp://bad.com" }]
    expect(extractResultUrls(results)).toEqual([])
  })

  it("deduplicates repeated URLs", () => {
    const results = [{ url: "https://a.com" }, { url: "https://a.com" }]
    const out = extractResultUrls(results)
    expect(out).toEqual(["https://a.com"])
    expect(out).toHaveLength(1)
  })
})

describe("createTrackingUrl", () => {
  it("produces a URL with the url param set to the content URL", () => {
    const result = createTrackingUrl("https://shop.example.com/product", {
      endpoint: "https://myagent.com/api/track",
    })
    const parsed = new URL(result)
    expect(parsed.origin + parsed.pathname).toBe(
      "https://myagent.com/api/track",
    )
    expect(parsed.searchParams.get("url")).toBe(
      "https://shop.example.com/product",
    )
  })

  it("includes session_id param when sessionId is provided", () => {
    const result = createTrackingUrl("https://shop.example.com/product", {
      endpoint: "https://myagent.com/api/track",
      sessionId: "conv-abc123",
    })
    const parsed = new URL(result)
    expect(parsed.searchParams.get("session_id")).toBe("conv-abc123")
  })

  it("throws when the endpoint is a relative path", () => {
    expect(() =>
      createTrackingUrl("https://example.com", { endpoint: "/api/track" }),
    ).toThrow()
  })
})
