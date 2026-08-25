import { describe, expect, it } from "vitest";
import { safeNextPath } from "../safeNextPath";

const ORIGIN = "https://ethiosci.app";

describe("safeNextPath", () => {
  it.each([
    ["", null],
    ["?next=", null],
    ["?next=/students", "/students"],
    ["?next=/students?tab=2#top", "/students?tab=2#top"],
    ["?next=//evil.com", null],
    ["?next=/%5Cevil.com", null],
    ["?next=/login?x=1", null],
    ["?next=https://evil.com/x", null],
    ["?next=https://ethiosci.app/students", "/students"],
    ["?next=https://%zz/", null],
    ["?next=javascript:alert(1)", null],
    ["?next=data:text/html,x", null],
    ["?next=/a&next=//evil.com", "/a"],
  ])("handles %s", (search, expected) => {
    expect(safeNextPath(search, ORIGIN)).toBe(expected);
  });
});
