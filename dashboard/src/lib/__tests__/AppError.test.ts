import { describe, expect, it } from "vitest";
import { ERROR_CATEGORIES, fromHttpStatus, isAppError } from "../errors/AppError";

describe("fromHttpStatus", () => {
  it("classifies common statuses", () => {
    expect(fromHttpStatus(401).category).toBe("authentication");
    expect(fromHttpStatus(401).retryable).toBe(false);
    expect(fromHttpStatus(403).category).toBe("authorization");
    expect(fromHttpStatus(404).category).toBe("not_found");
    expect(fromHttpStatus(409).category).toBe("conflict");
    expect(fromHttpStatus(422).category).toBe("validation");
    expect(fromHttpStatus(429).category).toBe("rate_limit");
    expect(fromHttpStatus(429).retryable).toBe(true);
    expect(fromHttpStatus(500).category).toBe("server");
    expect(fromHttpStatus(500).retryable).toBe(true);
    expect(fromHttpStatus(503).retryable).toBe(true);
    expect(fromHttpStatus(418).category).toBe("client");
    expect(fromHttpStatus(418).retryable).toBe(false);
    expect(fromHttpStatus(599).category).toBe("server");
  });
  it("preserves status", () => {
    expect(fromHttpStatus(401).status).toBe(401);
  });
});

describe("isAppError", () => {
  it("recognizes AppError-shaped values", () => {
    expect(isAppError(fromHttpStatus(500))).toBe(true);
  });
  it("rejects non-AppError values", () => {
    expect(isAppError(new Error("x"))).toBe(false);
    expect(isAppError(null)).toBe(false);
    expect(isAppError({ category: "server" })).toBe(false); // missing retryable
  });
  it("rejects unknown categories", () => {
    expect(isAppError({ category: "bogus", retryable: false })).toBe(false);
  });
  it("accepts every exported category", () => {
    for (const category of ERROR_CATEGORIES) {
      expect(isAppError({ category, retryable: false })).toBe(true);
    }
  });
});
