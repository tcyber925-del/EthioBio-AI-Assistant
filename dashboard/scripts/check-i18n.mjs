#!/usr/bin/env node
/**
 * i18n consistency check for the dashboard.
 *
 * Errors (exit 1):
 *   - duplicate keys in any messages/*.json file
 *   - keys referenced in code (useTranslations + t('...')) missing from en.json
 *   - keys present in a non-default locale but missing in en.json
 *
 * Warnings (exit 0 unless --strict):
 *   - keys present in en.json but missing in another locale (translation debt)
 *
 * Usage: node scripts/check-i18n.mjs [--strict]
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const DEFAULT_LOCALE = "en";

/** Parse JSON text, returning { data, duplicates: [{path, key}] }. */
export function parseJsonWithDuplicates(text) {
  let i = 0;
  const duplicates = [];

  function error(msg) {
    throw new SyntaxError(`${msg} at offset ${i}`);
  }
  function skipWs() {
    while (i < text.length && /\s/.test(text[i])) i++;
  }
  function parseString() {
    if (text[i] !== '"') error("expected string");
    i++;
    let out = "";
    while (i < text.length && text[i] !== '"') {
      if (text[i] === "\\") {
        i++;
        if (i >= text.length) error("bad escape");
        out += text[i]; // value content irrelevant for structure
      } else {
        out += text[i];
      }
      i++;
    }
    if (text[i] !== '"') error("unterminated string");
    i++;
    return out;
  }
  function parseValue(pathParts) {
    skipWs();
    const ch = text[i];
    if (ch === "{") return parseObject(pathParts);
    if (ch === "[") return parseArray(pathParts);
    if (ch === '"') return parseString();
    // number / true / false / null
    const m = /-?\d+(\.\d+)?([eE][+-]?\d+)?|true|false|null/.exec(text.slice(i));
    if (!m || m.index !== 0) error("unexpected token");
    i += m[0].length;
    return m[0];
  }
  function formatPath(parts) {
    return parts.reduce(
      (acc, p) => (typeof p === "number" ? `${acc}[${p}]` : acc ? `${acc}.${p}` : p),
      "",
    );
  }
  function parseObject(pathParts) {
    i++; // {
    const obj = {};
    const seen = new Set();
    skipWs();
    if (text[i] === "}") {
      i++;
      return obj;
    }
    for (;;) {
      skipWs();
      const key = parseString();
      if (seen.has(key)) {
        duplicates.push({ path: formatPath([...pathParts, key]), key });
      }
      seen.add(key);
      skipWs();
      if (text[i] !== ":") error("expected ':'");
      i++;
      obj[key] = parseValue([...pathParts, key]);
      skipWs();
      if (text[i] === ",") {
        i++;
        continue;
      }
      if (text[i] === "}") {
        i++;
        return obj;
      }
      error("expected ',' or '}'");
    }
  }
  function parseArray(pathParts) {
    i++; // [
    const arr = [];
    skipWs();
    if (text[i] === "]") {
      i++;
      return arr;
    }
    let idx = 0;
    for (;;) {
      arr.push(parseValue([...pathParts, idx]));
      idx++;
      skipWs();
      if (text[i] === ",") {
        i++;
        continue;
      }
      if (text[i] === "]") {
        i++;
        return arr;
      }
      error("expected ',' or ']'");
    }
  }

  const data = parseValue([]);
  skipWs();
  if (i < text.length) error("trailing content");
  return { data, duplicates };
}

/** Flatten nested message objects into { "ns.key": value }. */
export function flattenMessages(obj, prefix = "") {
  const out = {};
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === "object") Object.assign(out, flattenMessages(v, key));
    else out[key] = v;
  }
  return out;
}

/** Keys present in base but missing in other. */
export function findParityGaps(baseFlat, otherFlat) {
  return Object.keys(baseFlat).filter((k) => !(k in otherFlat)).sort();
}

const USE_TRANSLATIONS_RE = /useTranslations\(\s*['"]([\w.]+)['"]\s*\)/g;

/** Extract full dotted keys referenced via useTranslations-bound t() calls. */
export function extractReferencedKeys(sources) {
  const refs = new Set();
  for (const { code } of sources) {
    const vars = new Map(); // varName -> namespace
    for (const m of code.matchAll(/(?:const|let)\s+(\w+)\s*=\s*useTranslations\(\s*['"]([\w.]+)['"]\s*\)/g)) {
      vars.set(m[1], m[2]);
    }
    for (const [varName, ns] of vars) {
      const callRe = new RegExp(`\\b${varName}\\(\\s*['"]([\\w.]+)['"]\\s*[,)]`, "g");
      for (const m of code.matchAll(callRe)) {
        refs.add(ns ? `${ns}.${m[1]}` : m[1]);
      }
    }
  }
  return refs;
}

/** Run all checks. messages: {filename: rawText}, sources: [{path, code}]. */
export function runChecks({ messages, sources }) {
  const errors = [];
  const warnings = [];
  const flats = {};

  for (const [file, raw] of Object.entries(messages)) {
    const locale = path.basename(file, ".json");
    let parsed;
    try {
      parsed = parseJsonWithDuplicates(raw);
    } catch (e) {
      errors.push(`${file}: invalid JSON (${e.message})`);
      continue;
    }
    for (const d of parsed.duplicates) {
      errors.push(`${file}: duplicate key "${d.path}"`);
    }
    flats[locale] = flattenMessages(parsed.data);
  }

  const base = flats[DEFAULT_LOCALE];
  if (!base) {
    errors.push(`messages/${DEFAULT_LOCALE.json ?? "en.json"}: missing or unparsable`);
    return { errors, warnings };
  }

  // Code references must exist in the default locale.
  for (const key of extractReferencedKeys(sources)) {
    if (!(key in base)) {
      errors.push(`referenced in code but missing in ${DEFAULT_LOCALE}.json: "${key}"`);
    }
  }

  // Locale parity.
  for (const [locale, flat] of Object.entries(flats)) {
    if (locale === DEFAULT_LOCALE) continue;
    for (const k of findParityGaps(flat, base)) {
      errors.push(`${locale}.json has key missing from ${DEFAULT_LOCALE}.json: "${k}"`);
    }
    const gaps = findParityGaps(base, flat);
    if (gaps.length > 0) {
      warnings.push(
        `${locale}.json is missing ${gaps.length} keys present in ${DEFAULT_LOCALE}.json:\n    ` +
          gaps.join("\n    "),
      );
    }
  }

  return { errors, warnings };
}

/* ---------------------------------- CLI ---------------------------------- */

function collectSources(srcDir) {
  const out = [];
  (function walk(dir) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (entry.name === "node_modules" || entry.name === "__tests__") continue;
        walk(full);
      } else if (/\.(tsx?|jsx?)$/.test(entry.name) && !/\.(test|spec)\.tsx?$/.test(entry.name)) {
        out.push({ path: full, code: fs.readFileSync(full, "utf8") });
      }
    }
  })(srcDir);
  return out;
}

function main() {
  const strict = process.argv.includes("--strict");
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
  const messagesDir = path.join(root, "messages");
  const messages = {};
  for (const f of fs.readdirSync(messagesDir).filter((f) => f.endsWith(".json"))) {
    messages[f] = fs.readFileSync(path.join(messagesDir, f), "utf8");
  }
  const sources = collectSources(path.join(root, "src"));
  const { errors, warnings } = runChecks({ messages, sources });

  for (const w of warnings) console.warn(`WARN  ${w}`);
  for (const e of errors) console.error(`ERROR ${e}`);
  if (errors.length > 0 || (strict && warnings.length > 0)) {
    console.error(`\ni18n check failed: ${errors.length} errors, ${warnings.length} warnings`);
    process.exit(1);
  }
  console.log(`i18n check passed (${warnings.length} warnings)`);
}

if (
  process.argv[1] &&
  fs.realpathSync(fileURLToPath(import.meta.url)) ===
    fs.realpathSync(path.resolve(process.argv[1]))
) {
  main();
}
