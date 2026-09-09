import { describe, expect, it } from "vitest";
import {
  CONSENT_PENDING_PATH,
  resolvePostAuthDestination,
  resolvePostAuthDestinationOr,
  type PostAuthMe,
} from "../resolveDestination";

const done: PostAuthMe = { role_claimed: true, onboarding_completed: true };

describe("resolvePostAuthDestination", () => {
  it("routes unclaimed users back to the role picker", () => {
    expect(resolvePostAuthDestination({ role_claimed: false })).toBe("/sign-up");
  });

  it("routes role-claimed users without onboarding to /onboarding", () => {
    expect(resolvePostAuthDestination({ role_claimed: true, onboarding_completed: false })).toBe(
      "/onboarding",
    );
  });

  it("routes completed users to /v2/overview by default", () => {
    expect(resolvePostAuthDestination(done)).toBe("/v2/overview");
  });

  it("routes inactive accounts (under-13 consent) to consent-pending", () => {
    expect(resolvePostAuthDestination({ ...done, is_active: false })).toBe(CONSENT_PENDING_PATH);
  });

  it("honors a safe requestedNext before the default", () => {
    expect(resolvePostAuthDestination(done, "/students?tab=2")).toBe("/students?tab=2");
  });

  it("falls back to /v2/overview for an unsafe or missing next", () => {
    expect(resolvePostAuthDestination(done, "https://evil.com")).toBe("/v2/overview");
    expect(resolvePostAuthDestination(done, null)).toBe("/v2/overview");
  });

  it("returns null-ish me to the requested next when safe, else the default", () => {
    expect(resolvePostAuthDestination(null, "/students")).toBe("/students");
    expect(resolvePostAuthDestination(null, null)).toBe("/v2/overview");
  });
});

describe("resolvePostAuthDestinationOr", () => {
  it("routes a user_inactive failure to consent-pending", () => {
    expect(
      resolvePostAuthDestinationOr(null, { code: "auth_user_inactive" }, "/students"),
    ).toBe(CONSENT_PENDING_PATH);
  });

  it("falls through to the default on other failures", () => {
    expect(resolvePostAuthDestinationOr(null, { code: "auth_token_expired" })).toBe(
      "/v2/overview",
    );
    expect(resolvePostAuthDestinationOr(null, new Error("network"))).toBe("/v2/overview");
  });

  it("still prefers me state over a benign failure", () => {
    expect(
      resolvePostAuthDestinationOr({ role_claimed: false }, new Error("network")),
    ).toBe("/sign-up");
  });
});