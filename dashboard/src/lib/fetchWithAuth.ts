import * as fwa from "./fetchWithAuth";
import { normalizeHttpError } from "./errors";

const REFRESH_URL = "/auth/refresh";
const NO_REDIRECT_PREFIXES = [
  "/login",
  "/auth/refresh",
  "/auth/token",
  "/auth/request-otp",
  "/auth/verify-otp",
  "/auth/register",
  "/auth/logout",
  "/auth/oauth",
];

let refreshPromise: Promise<boolean> | null = null;

function singleFlightRefresh(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = fetch(REFRESH_URL, { method: "POST", credentials: "include" })
      .then((r) => r.ok)
      .catch(() => false)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

function redirectToLogin(): void {
  if (typeof window === "undefined") return;
  const current = window.location.pathname + window.location.search;
  if (current === "/login" || current.startsWith("/login/")) return;
  window.location.href = `/login?next=${encodeURIComponent(current)}`;
}

export { redirectToLogin }; // exported for tests; do not import elsewhere

function authorized(url: string, options: RequestInit = {}): [string, RequestInit] {
  const headers = { "Content-Type": "application/json", ...(options.headers ?? {}) };
  return [url, { ...options, credentials: "include", headers }];
}

export async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const [authUrl, authOpts] = authorized(url, options);
  let res = await fetch(authUrl, authOpts);
  if (res.status !== 401) return res;
  if (NO_REDIRECT_PREFIXES.some((p) => url.startsWith(p))) return res;
  const refreshed = await singleFlightRefresh();
  if (refreshed) {
    res = await fetch(authUrl, authOpts);
    if (res.status !== 401) return res;
  }
  fwa.redirectToLogin();
  return res;
}

export async function fetchWithAuthJson<T = unknown>(url: string, options: RequestInit = {}): Promise<T> {
  const res = await fetchWithAuth(url, options);
  const text = await res.text().catch(() => "");
  if (!res.ok) throw normalizeHttpError(res.status, text);
  try {
    return (text ? JSON.parse(text) : null) as T;
  } catch {
    throw { category: "service", code: "malformed_response", retryable: true } as const;
  }
}
