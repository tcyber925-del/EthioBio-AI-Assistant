import { marked } from "marked";

const ENTITY_DECODE: Record<string, string> = {
  "&amp;": "&",
  "&lt;": "<",
  "&gt;": ">",
  "&quot;": '"',
  "&#39;": "'",
  "&#x27;": "'",
  "&nbsp;": " ",
};

export function markdownToPlainText(markdown: string): string {
  if (!markdown) return "";
  const html = marked.parse(markdown, { async: false }) as string;
  const text = html
    .replace(/<[^>]*>/g, " ")
    .replace(/&(amp|lt|gt|quot|#39|#x27|nbsp);/g, (m) => ENTITY_DECODE[m]);
  return text.replace(/\s+/g, " ").trim();
}