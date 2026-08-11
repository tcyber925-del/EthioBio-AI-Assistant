export type ErrorCategory =
    | "authentication"
    | "authorization"
    | "validation"
    | "conflict"
    | "not_found"
    | "rate_limit"
    | "network"
    | "server"
    | "service"
    | "client"
    | "unknown";

export interface AppError {
    category: ErrorCategory;
    code?: string;
    status?: number;
    retryable: boolean;
    retryAfter?: number;
    fieldErrors?: Record<string, string[]>;
    params?: Record<string, unknown>;
    requestId?: string;
    cause?: unknown;
}

const SERVER_STATUS = new Set<number>([500, 502, 503, 504, 599]);

export function fromHttpStatus(status: number): AppError {
    if (status === 401) return { category: "authentication", status, retryable: false };
    if (status === 403) return { category: "authorization", status, retryable: false };
    if (status === 404) return { category: "not_found", status, retryable: false };
    if (status === 409) return { category: "conflict", status, retryable: false };
    if (status === 422) return { category: "validation", status, retryable: false };
    if (status === 429) return { category: "rate_limit", status, retryable: true };
    if (SERVER_STATUS.has(status)) return { category: "server", status, retryable: true };
    if (status >= 400 && status < 500) return { category: "client", status, retryable: false };
    return { category: "unknown", status, retryable: false };
}

export function isAppError(value: unknown): value is AppError {
    if (typeof value !== "object" || value === null) return false;
    const v = value as Record<string, unknown>;
    return typeof v.category === "string" && typeof v.retryable === "boolean";
}