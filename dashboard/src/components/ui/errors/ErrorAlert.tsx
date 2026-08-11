"use client";

import { AlertTriangle } from "lucide-react";
import { useTranslations } from "next-intl";
import Button from "@/components/ui/Button";
import { useErrorMessage } from "@/hooks/useErrorMessage";
import type { AppError } from "@/lib/errors";

interface ErrorAlertProps {
  error: AppError | null;
  title?: string;
  onRetry?: () => void;
  retrying?: boolean;
  className?: string;
}

export function ErrorAlert({ error, title, onRetry, retrying, className = "" }: ErrorAlertProps) {
  const t = useTranslations("errors");
  const message = useErrorMessage(error);
  if (!error) return null;
  return (
    <div
      role="alert"
      className={`flex items-start gap-2 text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2 ${className}`}
    >
      <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        {title && <p className="font-medium text-red-400">{title}</p>}
        <p>{message}</p>
      </div>
      {onRetry && (
        <Button variant="danger" size="sm" onClick={onRetry} loading={retrying} className="flex-shrink-0">
          {t("retry")}
        </Button>
      )}
    </div>
  );
}
