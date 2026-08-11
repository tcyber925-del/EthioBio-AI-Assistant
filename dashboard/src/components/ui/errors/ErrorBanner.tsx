"use client";

import { useTranslations } from "next-intl";
import Button from "@/components/ui/Button";
import { useErrorMessage } from "@/hooks/useErrorMessage";
import type { AppError } from "@/lib/errors";

interface ErrorBannerProps {
  error: AppError;
  onAction?: () => void;
  actionLabel?: string;
}

export function ErrorBanner({ error, onAction, actionLabel }: ErrorBannerProps) {
  const t = useTranslations();
  const message = useErrorMessage(error);
  return (
    <div role="alert" className="flex items-center justify-between gap-4 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 text-sm text-red-400">
      <p>{message}</p>
      {onAction && (
        <Button variant="danger" size="sm" onClick={onAction}>
          {actionLabel ?? t("common.retry")}
        </Button>
      )}
    </div>
  );
}
