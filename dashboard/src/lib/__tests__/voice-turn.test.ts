import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { voiceTurnFetch } from "../voice-turn";

const sse = (chunks: string[]) => {
  const encoder = new TextEncoder();
  return {
    ok: true,
    status: 200,
    text: () => Promise.resolve(""),
    body: new ReadableStream({
      start(controller) {
        for (const c of chunks) controller.enqueue(encoder.encode(c));
        controller.close();
      },
    }),
  } as unknown as Response;
};

const callbacks = () => ({
  onError: vi.fn(),
  onSttTranscript: vi.fn(),
  onToken: vi.fn(),
  onAudio: vi.fn(),
  onMetadata: vi.fn(),
  onDone: vi.fn(),
});

describe("voiceTurnFetch — structured AppError delivery", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    localStorage.clear();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("non-ok JSON detail → structured AppError", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 429,
      text: () => Promise.resolve('{"detail":"Slow down"}'),
    } as unknown as Response);
    const cb = callbacks();
    await voiceTurnFetch(new Blob(["x"], { type: "audio/webm" }), 12, "en", "", cb);
    expect(cb.onError).toHaveBeenCalledWith(expect.objectContaining({ category: "rate_limit", status: 429, retryable: true }));
  });

  it("non-ok empty body → fromHttpStatus fallback", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: () => Promise.resolve(""),
    } as unknown as Response);
    const cb = callbacks();
    await voiceTurnFetch(new Blob(["x"], { type: "audio/webm" }), 12, "en", "", cb);
    expect(cb.onError).toHaveBeenCalledWith(expect.objectContaining({ category: "server", status: 500, retryable: true }));
  });

  it("chunk.error → service retryable AppError", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      sse(['data: {"delta":"","node":"tutor","done":false,"error":"upstream failure","status":false}\n']),
    );
    const cb = callbacks();
    await voiceTurnFetch(new Blob(["x"], { type: "audio/webm" }), 12, "en", "", cb);
    expect(cb.onError).toHaveBeenCalledWith({ category: "service", retryable: true });
    expect(cb.onDone).not.toHaveBeenCalled();
  });

  it("missing response body → service AppError", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({ ok: true, status: 200, body: null } as unknown as Response);
    const cb = callbacks();
    await voiceTurnFetch(new Blob(["x"], { type: "audio/webm" }), 12, "en", "", cb);
    expect(cb.onError).toHaveBeenCalledWith(expect.objectContaining({ category: "service", retryable: true }));
  });

  it("network rejection → network AppError", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError("Failed to fetch"));
    const cb = callbacks();
    await voiceTurnFetch(new Blob(["x"], { type: "audio/webm" }), 12, "en", "", cb);
    expect(cb.onError).toHaveBeenCalledWith(expect.objectContaining({ category: "network", retryable: true }));
  });

  it("AbortError → silent cancel, no onError", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new DOMException("The operation was aborted.", "AbortError"));
    const cb = callbacks();
    await voiceTurnFetch(new Blob(["x"], { type: "audio/webm" }), 12, "en", "", cb);
    expect(cb.onError).not.toHaveBeenCalled();
  });

  it("stream read rejection → network AppError", async () => {
    const encoder = new TextEncoder();
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      status: 200,
      text: () => Promise.resolve(""),
      body: new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode("data: {"));
          controller.error(new TypeError("network reset"));
        },
      }),
    } as unknown as Response);
    const cb = callbacks();
    await voiceTurnFetch(new Blob(["x"], { type: "audio/webm" }), 12, "en", "", cb);
    expect(cb.onError).toHaveBeenCalledWith(expect.objectContaining({ category: "network", retryable: true }));
  });
});