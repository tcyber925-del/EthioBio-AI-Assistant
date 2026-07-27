type Messages = Record<string, unknown>;

function isPlainObject(v: unknown): v is Messages {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

/**
 * Deep-merge message catalogs: every key in `base` (the default locale)
 * survives unless `override` (the active locale) provides a value for it.
 * Arrays and scalars are replaced wholesale, never merged element-wise.
 */
export function deepMergeMessages(base: Messages, override: Messages): Messages {
  const out: Messages = { ...base };
  for (const [key, value] of Object.entries(override)) {
    const baseValue = out[key];
    out[key] =
      isPlainObject(baseValue) && isPlainObject(value)
        ? deepMergeMessages(baseValue, value)
        : value;
  }
  return out;
}
