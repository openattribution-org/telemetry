import { describe, it, expect, vi, beforeEach } from "vitest"
import { MCPSessionTracker } from "../mcp.js"

const mockClient = {
  startSession: vi.fn().mockResolvedValue("session-uuid-123"),
  recordEvents: vi.fn().mockResolvedValue(undefined),
  recordEvent: vi.fn().mockResolvedValue(undefined),
  endSession: vi.fn().mockResolvedValue(undefined),
}

// Cast to satisfy the TelemetryClient type without importing it
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const tracker = () => new MCPSessionTracker(mockClient as any)

beforeEach(() => {
  vi.clearAllMocks()
})

describe("MCPSessionTracker.getOrCreateSession", () => {
  it("calls startSession once for a new externalSessionId and returns the session ID", async () => {
    const t = tracker()
    const sessionId = await t.getOrCreateSession("user-abc")
    expect(mockClient.startSession).toHaveBeenCalledTimes(1)
    expect(sessionId).toBe("session-uuid-123")
  })

  it("reuses the cached session for the same externalSessionId", async () => {
    const t = tracker()
    const first = await t.getOrCreateSession("user-abc")
    const second = await t.getOrCreateSession("user-abc")
    expect(mockClient.startSession).toHaveBeenCalledTimes(1)
    expect(first).toBe(second)
  })

  it("calls startSession each time when externalSessionId is undefined", async () => {
    const t = tracker()
    await t.getOrCreateSession(undefined)
    await t.getOrCreateSession(undefined)
    expect(mockClient.startSession).toHaveBeenCalledTimes(2)
  })
})

describe("MCPSessionTracker.trackRetrieved", () => {
  it("does nothing when urls is empty", async () => {
    const t = tracker()
    await t.trackRetrieved("user-abc", [])
    expect(mockClient.startSession).not.toHaveBeenCalled()
    expect(mockClient.recordEvents).not.toHaveBeenCalled()
  })

  it("calls recordEvents with content_retrieved events for each URL", async () => {
    const t = tracker()
    await t.trackRetrieved("user-abc", [
      "https://a.com",
      "https://b.com",
    ])
    expect(mockClient.recordEvents).toHaveBeenCalledTimes(1)
    const [sessionId, events] = mockClient.recordEvents.mock.calls[0]
    expect(sessionId).toBe("session-uuid-123")
    expect(events).toHaveLength(2)
    expect(events[0].type).toBe("content_retrieved")
    expect(events[0].contentUrl).toBe("https://a.com")
    expect(events[1].contentUrl).toBe("https://b.com")
  })
})

describe("MCPSessionTracker.trackCited", () => {
  it("calls recordEvents with content_cited events for each URL", async () => {
    const t = tracker()
    await t.trackCited("user-abc", ["https://a.com"])
    expect(mockClient.recordEvents).toHaveBeenCalledTimes(1)
    const [, events] = mockClient.recordEvents.mock.calls[0]
    expect(events).toHaveLength(1)
    expect(events[0].type).toBe("content_cited")
    expect(events[0].contentUrl).toBe("https://a.com")
  })
})

describe("MCPSessionTracker.sessionCount", () => {
  it("returns the correct count after sessions are created", async () => {
    const t = tracker()
    expect(t.sessionCount).toBe(0)
    await t.getOrCreateSession("user-1")
    expect(t.sessionCount).toBe(1)
    await t.getOrCreateSession("user-2")
    expect(t.sessionCount).toBe(2)
    // Same ID — no new entry
    await t.getOrCreateSession("user-1")
    expect(t.sessionCount).toBe(2)
  })
})
