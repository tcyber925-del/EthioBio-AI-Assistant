import { fromHttpStatus, type AppError } from "./AppError";

const VALIDATION_TYPE_MAP: Record<string, string> = {
  missing: "errors.validation.missing",
  string_type: "errors.validation.string_type",
  integer_type: "errors.validation.integer_type",
  value_error: "errors.validation.value_error",
};

function classifyHttp(status: number, body: unknown): AppError {
  const base = fromHttpStatus(status);
  if (typeof body === "object" && body !== null) {
    const b = body as Record<string, unknown>;
    const inner = b.error;
    if (typeof inner === "object" && inner !== null) {
      const e = inner as Record<string, unknown>;
      const context = (typeof e.context === "object" && e.context !== null ? e.context : {}) as Record<string, unknown>;
      const retryAfter = typeof context.retry_after === "number" ? context.retry_after : undefined;
      const error: AppError = { ...base, code: typeof e.code === "string" ? e.code : undefined, params: {} };
      if (retryAfter !== undefined) error.retryAfter = retryAfter;
      return error;
    }
    if (Array.isArray(b.detail)) {
      const fieldErrors: Record<string, string[]> = {};
      for (const item of b.detail as Array<Record<string, unknown>>) {
        const loc = item.loc;
        const type = typeof item.type === "string" ? item.type : "";
        const key = VALIDATION_TYPE_MAP[type] ?? "errors.validation.generic";
        if (!Array.isArray(loc) || loc.length === 0) continue;
        const field = loc
          .filter((s) => String(s) !== "body" && String(s) !== "query" && String(s) !== "path")
          .map((s) => String(s))
          .join(".");
        if (!field) continue;
        (fieldErrors[field] ??= []).push(key);
      }
      return { ...base, fieldErrors };
    }
  }
  return base;
}

export function normalizeHttpError(status: number, bodyText: string): AppError {
  if (!bodyText.trim()) return fromHttpStatus(status);
  try {
    const parsed: unknown = JSON.parse(bodyText);
    return classifyHttp(status, parsed);
  } catch {
    return fromHttpStatus(status);
  }
}

export function normalizeException(error: unknown): AppError {
  if (error instanceof Error && (error.name === "AbortError" || error.name === "TimeoutError")) {
    return { category: "network", retryable: true, cause: error };
  }
  if (error instanceof TypeError && /fetch|network|failed/i.test(error.message)) {
    return { category: "network", retryable: true, cause: error };
  }
  if (error instanceof Error) {
    return { category: "unknown", retryable: false, cause: error };
  }
  return { category: "unknown", retryable: false, cause: error };
}

export function normalizeStreamError(code: string): AppError {
  return { category: "service", code: code || undefined, retryable: true };
}
