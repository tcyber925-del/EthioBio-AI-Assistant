"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";
import Button from "@/components/ui/Button";
import { useErrorMessage } from "@/hooks/useErrorMessage";
import type { AppError } from "@/lib/errors";

interface ErrorStateProps {
  error: AppError | null;
  title?: string;
  onRetry?: () => void;
  retrying?: boolean;
  className?: string;
}

export function ErrorState({ error, title, onRetry, retrying, className = "" }: ErrorStateProps) {
  const t = useTranslations();
  const message = useErrorMessage(error);
  if (!error) return null;
  return (
    <div role="alert" className={`text-center py-16 ${className}`}>
      <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" aria-hidden="true" />
      <p className="font-medium text-foreground">{title ?? t("errors.error_title")}</p>
      <p className="text-foreground-muted mt-1">{message}</p>
      {onRetry && error.retryable && (
        <Button variant="danger" onClick={onRetry} loading={retrying} className="mt-4">
          <RefreshCw className="w-4 h-4" aria-hidden="true" />
          {t("common.retry")}
        </Button>
      )}
    </div>
  );
}
