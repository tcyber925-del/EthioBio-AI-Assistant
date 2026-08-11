import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchWithAuth } from "../fetchWithAuth";
import * as fwa from "../fetchWithAuth";

const ok = (body = "{}") => ({ ok: true, status: 200, text: () => Promise.resolve(body) });

describe("fetchWithAuth", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    localStorage.clear();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
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
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any)
      .mockResolvedValueOnce(ok() as any) // refresh
      .mockResolvedValueOnce(ok() as any) // retry A
      .mockResolvedValueOnce(ok() as any); // retry B
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

  it("redirects to /login?next=... when refresh fails (once)", async () => {
    const spy = vi.spyOn(fwa, "redirectToLogin").mockImplementation(() => {});
    vi.mocked(fetch)
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any)
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any);
    await fetchWithAuth("/api/students");
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it("skips redirect when already on /login", async () => {
    Object.defineProperty(window, "location", {
      value: { pathname: "/login", search: "", href: "http://x/login" },
      configurable: true,
    });
    vi.mocked(fetch)
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any)
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any);
    await fetchWithAuth("/api/students");
    expect(window.location.href).toBe("http://x/login");
  });
});
