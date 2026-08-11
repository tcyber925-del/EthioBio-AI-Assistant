import { describe, expect, it } from "vitest";
import { normalizeException, normalizeHttpError, normalizeStreamError } from "../errors/normalizeError";

const envelope = (status: number, code: string, detail: string, context?: Record<string, unknown>) =>
  JSON.stringify({ error: { code, detail, context: context ?? {} } });

describe("normalizeHttpError — structured envelope", () => {
  it("401 with known code preserves code", () => {
    const err = normalizeHttpError(401, envelope(401, "auth_invalid_credentials", "Invalid email or password"));
    expect(err.category).toBe("authentication");
    expect(err.code).toBe("auth_invalid_credentials");
    expect(err.status).toBe(401);
    expect(err.retryable).toBe(false);
  });
  it("429 with retry_after carries retryAfter", () => {
    const err = normalizeHttpError(429, envelope(429, "rate_limit_exceeded", "Slow down", { retry_after: 42 }));
    expect(err.category).toBe("rate_limit");
    expect(err.retryable).toBe(true);
    expect(err.retryAfter).toBe(42);
  });
  it("drops unsafe context params", () => {
    const err = normalizeHttpError(500, envelope(500, "internal_error", "boom", { retry_after: 5, secret: "hunter2" }));
    expect(err.params).toEqual({});
    expect(err.retryAfter).toBe(5);
  });
  it("preserves retry_after of 0", () => {
    const err = normalizeHttpError(429, envelope(429, "rate_limit_exceeded", "x", { retry_after: 0 }));
    expect(err.retryAfter).toBe(0);
  });
});

describe("normalizeHttpError — FastAPI string detail", () => {
  it("401 string detail", () => {
    const err = normalizeHttpError(401, JSON.stringify({ detail: "Incorrect username or password" }));
    expect(err.category).toBe("authentication");
    expect(err.status).toBe(401);
  });
  it("500 string detail never leaks into message surface", () => {
    const err = normalizeHttpError(500, JSON.stringify({ detail: "pg_dump failed (exit 1): FATAL: connection refused" }));
    expect(err.category).toBe("server");
    expect(err.cause).toBeUndefined();
  });
});

describe("normalizeHttpError — Pydantic validation", () => {
  it("maps loc to fieldErrors with catalog keys", () => {
    const body = JSON.stringify({
      detail: [
        { loc: ["body", "email"], msg: "value is not a valid email", type: "value_error" },
        { loc: ["body", "email"], msg: "field required", type: "missing" },
      ],
    });
    const err = normalizeHttpError(422, body);
    expect(err.category).toBe("validation");
    expect(err.status).toBe(422);
    expect(err.fieldErrors).toEqual({
      email: ["errors.validation.value_error", "errors.validation.missing"],
    });
  });
  it("skips non-body loc segments and maps unknown types to generic", () => {
    const body = JSON.stringify({
      detail: [{ loc: ["query", "x"], msg: "boom", type: "weird_type" }],
    });
    const err = normalizeHttpError(400, body);
    expect(err.fieldErrors).toEqual({ x: ["errors.validation.generic"] });
  });
  it("maps numeric loc segments for list items", () => {
    const body = JSON.stringify({
      detail: [{ loc: ["body", "items", 0, "name"], msg: "x", type: "missing" }],
    });
    const err = normalizeHttpError(422, body);
    expect(err.fieldErrors).toEqual({ "items.0.name": ["errors.validation.missing"] });
  });
});

describe("normalizeHttpError — plain/ad-hoc/malformed", () => {
  it("ad-hoc {error: string}", () => {
    const err = normalizeHttpError(503, JSON.stringify({ error: "bot not ready" }));
    expect(err.category).toBe("server");
    expect(err.status).toBe(503);
    expect(err.retryable).toBe(true);
  });
  it("plain text body", () => {
    const err = normalizeHttpError(502, "Bad Gateway");
    expect(err.category).toBe("server");
  });
  it("malformed JSON", () => {
    const err = normalizeHttpError(500, "{not json");
    expect(err.category).toBe("server");
  });
  it("empty body", () => {
    const err = normalizeHttpError(401, "");
    expect(err.category).toBe("authentication");
  });
});

describe("normalizeException", () => {
  it("AbortError → network retryable", () => {
    const abort = new DOMException("The operation was aborted.", "AbortError");
    const err = normalizeException(abort);
    expect(err.category).toBe("network");
    expect(err.retryable).toBe(true);
  });
  it("fetch TypeError → network retryable", () => {
    const err = normalizeException(new TypeError("Failed to fetch"));
    expect(err.category).toBe("network");
    expect(err.retryable).toBe(true);
  });
  it("generic Error → unknown, cause preserved", () => {
    const original = new Error("whatever");
    const err = normalizeException(original);
    expect(err.category).toBe("unknown");
    expect(err.retryable).toBe(false);
    expect(err.cause).toBe(original);
  });
  it("non-Error throw (string) → unknown", () => {
    const err = normalizeException("boom");
    expect(err.category).toBe("unknown");
  });
});

describe("normalizeStreamError", () => {
  it("maps stream error codes to service category", () => {
    const err = normalizeStreamError("model_timeout");
    expect(err.category).toBe("service");
    expect(err.code).toBe("model_timeout");
    expect(err.retryable).toBe(true);
  });
  it("handles empty code", () => {
    const err = normalizeStreamError("");
    expect(err.category).toBe("service");
    expect(err.code).toBeUndefined();
  });
});
