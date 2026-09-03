import { getToken } from "./auth";
import { normalizeHttpError } from "./errors";

const NO_REDIRECT_PREFIXES = ["/login", "/sign-in", "/sign-up", "/sso-callback"];

function redirectToSignIn(): void {
  if (typeof window === "undefined") return;
  const current = window.location.pathname + window.location.search;
  if (current.startsWith("/login") || current.startsWith("/sign-in")) return;
  window.location.href = `/sign-in?next=${encodeURIComponent(current)}`;
}

function authorized(url: string, options: RequestInit = {}): [string, RequestInit] {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers ?? {}),
  } as Record<string, string>;
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return [url, { ...options, credentials: "include", headers }];
}

export async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const [authUrl, authOpts] = authorized(url, options);
  const res = await fetch(authUrl, authOpts);
  if (res.status === 401 && !NO_REDIRECT_PREFIXES.some((p) => url.startsWith(p))) {
    redirectToSignIn();
  }
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