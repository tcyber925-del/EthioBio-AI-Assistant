"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";
import { useTranslations } from "next-intl";

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const t = useTranslations("errors");

  useEffect(() => {
    if (process.env.NODE_ENV !== "production") {
      console.error("route render error", error);
    }
  }, [error]);

  return (
    <div role="alert" className="min-h-[40vh] flex flex-col items-center justify-center text-center px-4">
      <AlertTriangle className="w-10 h-10 text-red-400 mb-3" aria-hidden="true" />
      <h1 className="text-lg font-semibold text-foreground">{t("error_title")}</h1>
      <p className="text-sm text-foreground-muted mt-1">{t("boundary_message")}</p>
      <button
        onClick={reset}
        className="mt-4 px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover transition-colors"
        type="button"
      >
        {t("refresh_page")}
      </button>
    </div>
  );
}
