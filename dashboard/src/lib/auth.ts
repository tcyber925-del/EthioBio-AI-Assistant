export function isAuthenticated(): boolean {
  const tokenMatch = document.cookie.includes("access_token=");
  const flagMatch = document.cookie.includes("auth_ready=1");
  return tokenMatch && flagMatch;
}

export function getToken(): string | null {
  return null;
}

export function setToken(token: string): void {
}

export function clearToken(): void {
  fetch("/auth/logout", { method: "POST", credentials: "include" });
}

export function decodeToken(): { sub?: string; role?: string } | null {
  return null;
}

export function getUserId(): string | null {
  return null;
}

export function getUserRole(): string {
  const match = document.cookie.match(/(?:^|;\s*)user_role=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}
