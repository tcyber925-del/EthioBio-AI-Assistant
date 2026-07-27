import { describe, expect, it } from "vitest";
import {
  extractReferencedKeys,
  findParityGaps,
  flattenMessages,
  parseJsonWithDuplicates,
  runChecks,
} from "../check-i18n.mjs";

describe("parseJsonWithDuplicates", () => {
  it("parses valid JSON and reports no duplicates", () => {
    // Note: scalars are returned as raw text — only keys/structure matter here.
    const { data, duplicates } = parseJsonWithDuplicates(
      '{"a": {"b": 1, "c": 2}, "d": "x"}',
    );
    expect(data).toEqual({ a: { b: "1", c: "2" }, d: "x" });
    expect(duplicates).toEqual([]);
  });

  it("detects a duplicate key inside a nested object with its full path", () => {
    const { duplicates } = parseJsonWithDuplicates(
      '{"a": {"b": "first", "b": "second"}}',
    );
    expect(duplicates).toEqual([{ path: "a.b", key: "b" }]);
  });

  it("does not flag the same key name used in different objects", () => {
    const { duplicates } = parseJsonWithDuplicates(
      '{"a": {"title": "x"}, "b": {"title": "y"}}',
    );
    expect(duplicates).toEqual([]);
  });

  it("handles escaped quotes and braces inside strings without false positives", () => {
    const { duplicates } = parseJsonWithDuplicates(
      '{"a": "he said \\"{b}\\": {", "list": [{"k": 1, "k": 2}]}',
    );
    expect(duplicates).toEqual([{ path: "list[0].k", key: "k" }]);
  });
});

describe("flattenMessages", () => {
  it("flattens nested objects into dotted keys", () => {
    expect(flattenMessages({ a: { b: "x", c: { d: "y" } }, e: "z" })).toEqual({
      "a.b": "x",
      "a.c.d": "y",
      e: "z",
    });
  });
});

describe("findParityGaps", () => {
  it("returns keys present in base but missing in other", () => {
    expect(
      findParityGaps({ "a.b": "x", "a.c": "y" }, { "a.b": "x" }),
    ).toEqual(["a.c"]);
  });
});

describe("extractReferencedKeys", () => {
  it("resolves t() calls against their useTranslations namespace", () => {
    const code = `
      const t = useTranslations('quiz')
      const tc = useTranslations('common')
      t('title') + tc('loading') + t('col_grade')
    `;
    const refs = extractReferencedKeys([{ path: "x.tsx", code }]);
    expect(refs).toEqual(
      new Set(["quiz.title", "common.loading", "quiz.col_grade"]),
    );
  });

  it("supports nested namespaces", () => {
    const code = `const t = useTranslations('admin.dashboard'); t('title')`;
    const refs = extractReferencedKeys([{ path: "x.tsx", code }]);
    expect(refs).toEqual(new Set(["admin.dashboard.title"]));
  });

  it("ignores dynamic (non-literal) keys", () => {
    const code = "const t = useTranslations('g'); t(meta.title); t(`x_${y}`)";
    const refs = extractReferencedKeys([{ path: "x.tsx", code }]);
    expect(refs).toEqual(new Set());
  });
});

describe("runChecks", () => {
  it("reports errors for duplicates, parity gaps and missing code refs", () => {
    const result = runChecks({
      messages: {
        "en.json": '{"a": {"x": "1", "x": "2"}, "b": "B"}',
        "am.json": '{"a": {"x": "1"}}',
      },
      sources: [{ path: "p.tsx", code: "const t = useTranslations('a'); t('missing')" }],
    });
    const text = [...result.errors, ...result.warnings].join("\n");
    expect(text).toContain("a.x");
    expect(text).toContain("b");
    expect(text).toContain("a.missing");
    expect(result.errors.length).toBeGreaterThan(0);
  });

  it("passes cleanly when messages and code are consistent", () => {
    const result = runChecks({
      messages: {
        "en.json": '{"a": {"x": "1"}}',
        "am.json": '{"a": {"x": "2"}}',
      },
      sources: [{ path: "p.tsx", code: "const t = useTranslations('a'); t('x')" }],
    });
    expect(result.errors).toEqual([]);
    expect(result.warnings).toEqual([]);
  });
});
