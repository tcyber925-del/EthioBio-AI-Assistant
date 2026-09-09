import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ageFromDob,
  clearSignupIntent,
  loadSignupIntent,
  normalizeRole,
  saveSignupIntent,
} from "../signupIntent";

const KEY = "ethiosci_signup_intent";

describe("normalizeRole", () => {
  it("maps the public term learner to student", () => {
    expect(normalizeRole("learner")).toBe("student");
  });

  it("accepts the API value student directly", () => {
    expect(normalizeRole("student")).toBe("student");
  });

  it("accepts teacher and parent", () => {
    expect(normalizeRole("teacher")).toBe("teacher");
    expect(normalizeRole("parent")).toBe("parent");
  });

  it("rejects unknown and missing values", () => {
    expect(normalizeRole("admin")).toBeNull();
    expect(normalizeRole(null)).toBeNull();
    expect(normalizeRole("")).toBeNull();
  });
});

describe("signupIntent draft (sessionStorage)", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("round-trips role/dob/parentEmail", () => {
    saveSignupIntent({ role: "student", dob: "2014-03-01", parentEmail: "p@example.com" });
    expect(loadSignupIntent()).toEqual({
      role: "student",
      dob: "2014-03-01",
      parentEmail: "p@example.com",
    });
  });

  it("returns null when no draft exists (wizard guard)", () => {
    expect(loadSignupIntent()).toBeNull();
  });

  it("drops drafts with an invalid role (storage corruption guard)", () => {
    sessionStorage.setItem(KEY, JSON.stringify({ role: "admin" }));
    expect(loadSignupIntent()).toBeNull();
  });

  it("clears the draft", () => {
    saveSignupIntent({ role: "teacher" });
    clearSignupIntent();
    expect(loadSignupIntent()).toBeNull();
  });

  it("tolerates storage being unavailable", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("quota");
    });
    expect(() => saveSignupIntent({ role: "parent" })).not.toThrow();
    expect(loadSignupIntent()).toBeNull();
  });
});

describe("ageFromDob", () => {
  it("computes whole years (boundary: birthday today)", () => {
    const today = new Date();
    const dob = `${today.getFullYear() - 13}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(
      today.getDate(),
    ).padStart(2, "0")}`;
    expect(ageFromDob(dob)).toBe(13);
  });

  it("is 12 the day before the 13th birthday", () => {
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const dob = `${today.getFullYear() - 13}-${String(tomorrow.getMonth() + 1).padStart(2, "0")}-${String(
      tomorrow.getDate(),
    ).padStart(2, "0")}`;
    expect(ageFromDob(dob)).toBe(12);
  });

  it("returns -1 for malformed input", () => {
    expect(ageFromDob("")).toBe(-1);
    expect(ageFromDob("not-a-date")).toBe(-1);
  });
});