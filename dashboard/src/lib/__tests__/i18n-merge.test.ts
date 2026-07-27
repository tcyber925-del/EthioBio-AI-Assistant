import { describe, expect, it } from "vitest";
import { deepMergeMessages } from "../i18n-merge";

describe("deepMergeMessages", () => {
  it("returns override values for keys present in both", () => {
    expect(deepMergeMessages({ a: "x" }, { a: "y" })).toEqual({ a: "y" });
  });

  it("keeps base keys missing from the override (locale fallback)", () => {
    const en = { common: { loading: "Loading...", retry: "Retry" } };
    const am = { common: { loading: "በመጫን ላይ..." } };
    expect(deepMergeMessages(en, am)).toEqual({
      common: { loading: "በመጫን ላይ...", retry: "Retry" },
    });
  });

  it("merges nested namespaces independently", () => {
    const en = { a: { x: "1", y: "2" }, b: { z: "3" } };
    const am = { a: { x: "አ" } };
    expect(deepMergeMessages(en, am)).toEqual({
      a: { x: "አ", y: "2" },
      b: { z: "3" },
    });
  });

  it("adds override-only keys and replaces (not merges) arrays", () => {
    expect(deepMergeMessages({ a: ["1", "2"] }, { a: ["3"], b: "new" })).toEqual({
      a: ["3"],
      b: "new",
    });
  });

  it("lets an explicit override win over a base object and vice versa", () => {
    expect(deepMergeMessages({ a: { x: "1" } }, { a: "flat" })).toEqual({ a: "flat" });
    expect(deepMergeMessages({ a: "flat" }, { a: { x: "1" } })).toEqual({ a: { x: "1" } });
  });
});
