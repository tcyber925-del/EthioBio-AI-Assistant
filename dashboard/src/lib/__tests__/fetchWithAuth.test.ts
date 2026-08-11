import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchWithAuth, fetchWithAuthJson } from "../fetchWithAuth";

const ok = (body = "{}") => ({ ok: true, status: 200, text: () => Promise.resolve(body) });

const originalLocation = window.location;

type LocationStub = { pathname: string; search: string; href: string; assign?: (url: string) => void };

const stubLocation = (value: LocationStub) => {
  Object.defineProperty(window, "location", { value, configurable: true });
};

describe("fetchWithAuth", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    localStorage.clear();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    Object.defineProperty(window, "location", { value: originalLocation, configurable: true });
  });

  it("returns non-401 responses untouched", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(ok() as any);
    const res = await fetchWithAuth("/api/students");
    expect(res.status).toBe(200);
    expect(fetch).toHaveBeenCalledWith("/api/students", expect.objectContaining({ credentials: "include" }));
  });

  it("refreshes once and retries on 401", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve('{"error":{"code":"auth_token_expired"}}') } as any)
      .mockResolvedValueOnce(ok() as any) // refresh
      .mockResolvedValueOnce(ok() as any); // retry
    const res = await fetchWithAuth("/api/students");
    expect(res.status).toBe(200);
    expect(fetch).toHaveBeenCalledWith("/auth/refresh", expect.objectContaining({ method: "POST" }));
  });

  it("single-flights concurrent 401s (one refresh call)", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any) // A initial
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any) // B initial
      .mockResolvedValueOnce(ok() as any) // shared refresh
      .mockResolvedValueOnce(ok() as any) // A retry
      .mockResolvedValueOnce(ok() as any); // B retry
    const [a, b] = await Promise.all([fetchWithAuth("/api/a"), fetchWithAuth("/api/b")]);
    expect(a.status).toBe(200);
    expect(b.status).toBe(200);
    const refreshCalls = vi.mocked(fetch).mock.calls.filter(([u]) => u === "/auth/refresh");
    expect(refreshCalls.length).toBe(1);
  });

  it("does not refresh for login/refresh URLs", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any);
    const res = await fetchWithAuth("/login");
    expect(res.status).toBe(401);
    expect(fetch).not.toHaveBeenCalledWith("/auth/refresh", expect.anything());
  });

  it("retries once then redirects when retry still 401s (no second refresh)", async () => {
    stubLocation({ pathname: "/classroom", search: "", href: "http://x/classroom", assign: vi.fn() });
    vi.mocked(fetch)
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any) // initial
      .mockResolvedValueOnce(ok() as any) // refresh
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any); // retry
    const res = await fetchWithAuth("/api/students");
    expect(res.status).toBe(401);
    const refreshCalls = vi.mocked(fetch).mock.calls.filter(([u]) => u === "/auth/refresh");
    expect(refreshCalls.length).toBe(1);
    expect(window.location.href).toBe("/login?next=%2Fclassroom");
  });

  it("redirects to /login?next=... when refresh fails", async () => {
    stubLocation({ pathname: "/classroom", search: "", href: "http://x/classroom", assign: vi.fn() });
    vi.mocked(fetch)
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any) // initial
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any); // refresh fail
    const res = await fetchWithAuth("/api/students");
    expect(res.status).toBe(401);
    expect(window.location.href).toBe("/login?next=%2Fclassroom");
  });

  it("skips redirect when already on /login", async () => {
    stubLocation({ pathname: "/login", search: "", href: "http://x/login" });
    vi.mocked(fetch)
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any)
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any);
    await fetchWithAuth("/api/students");
    expect(window.location.href).toBe("http://x/login");
  });

  it("skips redirect when on /login with a next param", async () => {
    stubLocation({ pathname: "/login", search: "?next=%2Fclassroom", href: "http://x/login?next=%2Fclassroom" });
    vi.mocked(fetch)
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any)
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any);
    await fetchWithAuth("/api/students");
    expect(window.location.href).toBe("http://x/login?next=%2Fclassroom");
  });
});

describe("fetchWithAuthJson", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("throws normalized AppError on non-ok", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({ ok: false, status: 500, text: () => Promise.resolve("boom") } as any);
    await expect(fetchWithAuthJson("/api/students")).rejects.toMatchObject({
      category: "server",
      status: 500,
      retryable: true,
    });
  });

  it("throws malformed_response on invalid JSON", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(ok("not json") as any);
    await expect(fetchWithAuthJson("/api/students")).rejects.toEqual({
      category: "service",
      code: "malformed_response",
      retryable: true,
    });
  });

  it("resolves null on empty body", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(ok("") as any);
    await expect(fetchWithAuthJson("/api/students")).resolves.toBeNull();
  });

  it("resolves parsed JSON on ok", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(ok('{"id": 1}') as any);
    await expect(fetchWithAuthJson("/api/students")).resolves.toEqual({ id: 1 });
  });
});
