"use client";

import { useTranslations } from "next-intl";
import type { AppError } from "@/lib/errors";

export interface MessageKey {
  key: string;
  params?: Record<string, string | number | Date>;
}

const GENERIC_KEY = "errors.generic";
const CATEGORY_KEY = (c: string): string => `errors.categories.${c}`;
const HTTP_KEY = (s: number): string => `errors.http.${s}`;
const CODE_KEY = (c: string): string => `errors.codes.${c}`;

const KNOWN_CODES = new Set([
  "auth_invalid_credentials",
  "auth_invalid_otp",
  "auth_otp_expired",
  "auth_token_expired",
  "auth_refresh_expired",
  "auth_user_inactive",
  "rate_limit_exceeded",
]);

export function errorMessageKeys(error: AppError): MessageKey {
  if (error.code && KNOWN_CODES.has(error.code)) return { key: CODE_KEY(error.code) };
  if (error.status) return { key: HTTP_KEY(error.status) };
  if (error.category === "unknown") return { key: GENERIC_KEY };
  return { key: CATEGORY_KEY(error.category) };
}

export function useErrorMessage(error: AppError | null | undefined): string {
  const t = useTranslations();
  if (!error) return "";
  const { key, params } = errorMessageKeys(error);
  return t(key, params);
}