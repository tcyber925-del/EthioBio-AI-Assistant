import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchWithAuth, fetchWithAuthJson } from "../fetchWithAuth";

const ok = (body = "{}") => ({ ok: true, status: 200, text: () => Promise.resolve(body) });

const originalLocation = window.location;

type LocationStub = { pathname: string; search: string; href: string; assign?: (url: string) => void };

const stubLocation = (value: LocationStub) => {
  Object.defineProperty(window, "location", { value, configurable: true });
};

const stubSession = (token: string | null) => {
  document.cookie = token ? `__session=${token}` : "__session=;max-age=0";
};

describe("fetchWithAuth", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    localStorage.clear();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    document.cookie = "__session=;max-age=0";
    Object.defineProperty(window, "location", { value: originalLocation, configurable: true });
  });

  it("returns non-401 responses untouched", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(ok() as any);
    const res = await fetchWithAuth("/api/students");
    expect(res.status).toBe(200);
    expect(fetch).toHaveBeenCalledWith("/api/students", expect.objectContaining({ credentials: "include" }));
  });

  it("attaches the Clerk session token as a Bearer header", async () => {
    stubSession("clerk-jwt-token");
    vi.mocked(fetch).mockResolvedValueOnce(ok() as any);
    await fetchWithAuth("/api/students");
    const init = vi.mocked(fetch).mock.calls[0]?.[1] as RequestInit;
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer clerk-jwt-token");
  });

  it("redirects to /sign-in?next=... on 401", async () => {
    stubLocation({ pathname: "/classroom", search: "", href: "http://x/classroom", assign: vi.fn() });
    vi.mocked(fetch).mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any);
    const res = await fetchWithAuth("/api/students");
    expect(res.status).toBe(401);
    expect(window.location.href).toBe("/sign-in?next=%2Fclassroom");
  });

  it("does not refresh on 401 (Clerk manages sessions)", async () => {
    stubLocation({ pathname: "/classroom", search: "", href: "http://x/classroom", assign: vi.fn() });
    vi.mocked(fetch).mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any);
    await fetchWithAuth("/api/students");
    expect(fetch).not.toHaveBeenCalledWith("/auth/refresh", expect.anything());
  });

  it("skips redirect for sign-in/login prefixes", async () => {
    stubLocation({ pathname: "/sign-in", search: "", href: "http://x/sign-in" });
    vi.mocked(fetch).mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any);
    const res = await fetchWithAuth("/sign-in?next=%2Fclassroom");
    expect(res.status).toBe(401);
    expect(window.location.href).toBe("http://x/sign-in");
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