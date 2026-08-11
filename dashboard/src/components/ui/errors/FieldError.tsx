"use client";

import { useTranslations } from "next-intl";

interface FieldErrorProps {
  id: string;
  field: string;
  messages: string[];
  className?: string;
}

export function FieldError({ id, field, messages, className = "" }: FieldErrorProps) {
  const t = useTranslations();
  if (!messages.length) return null;
  return (
    <span id={id} aria-live="polite" className={`text-sm text-red-400 block mt-1 ${className}`}>
      {messages.map((key, i) => (
        <span key={`${key}-${i}`} className="block">
          {t(key, { field })}
        </span>
      ))}
    </span>
  );
}
