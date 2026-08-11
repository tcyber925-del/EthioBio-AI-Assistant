export function safeNextPath(search: string, origin: string): string | null {
  const next = new URLSearchParams(search).get("next");
  if (!next) return null;
  try {
    const target = new URL(next, origin);
    if (target.origin !== new URL(origin).origin) return null;
    if (target.pathname.startsWith("/login")) return null;
    return target.pathname + target.search + target.hash;
  } catch {
    return null;
  }
}
