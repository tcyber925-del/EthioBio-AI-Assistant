import { describe, expect, it } from "vitest";
import { markdownToPlainText } from "../markdownToPlainText";

describe("markdownToPlainText", () => {
  it("strips heading markers", () => {
    expect(markdownToPlainText("# The Cell")).toBe("The Cell");
  });

  it("strips bold and italic emphasis", () => {
    expect(markdownToPlainText("**mitochondria** and *ribosomes*")).toBe(
      "mitochondria and ribosomes",
    );
  });

  it("keeps link text and drops the URL", () => {
    expect(markdownToPlainText("[EthioBio](https://ethiobio.ai)")).toBe(
      "EthioBio",
    );
  });

  it("turns bullet lists into plain lines", () => {
    expect(markdownToPlainText("- DNA\n- RNA")).toBe("DNA RNA");
  });

  it("keeps code content and drops the fence", () => {
    expect(markdownToPlainText("```js\nconst x = 1\n```")).toBe("const x = 1");
  });

  it("flattens tables to cell text", () => {
    expect(markdownToPlainText("| A | B |\n|---|---|\n| 1 | 2 |")).toBe(
      "A B 1 2",
    );
  });

  it("decodes HTML entities", () => {
    expect(markdownToPlainText("DNA & RNA")).toBe("DNA & RNA");
  });

  it("collapses whitespace and trims", () => {
    expect(markdownToPlainText("  line1\n\n   line2  ")).toBe("line1 line2");
  });

  it("returns an empty string for empty input", () => {
    expect(markdownToPlainText("")).toBe("");
  });
});
