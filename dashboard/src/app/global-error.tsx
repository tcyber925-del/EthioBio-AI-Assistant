"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";
import { useTranslations } from "next-intl";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const t = useTranslations("errors");

  useEffect(() => {
    if (process.env.NODE_ENV !== "production") {
      console.error("global error", error);
    }
  }, [error]);

  return (
    <html lang="en">
      <body className="min-h-screen flex items-center justify-center bg-background">
        <div role="alert" className="text-center px-4">
          <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" aria-hidden="true" />
          <h1 className="text-lg font-semibold text-foreground">{t("error_title")}</h1>
          <p className="text-sm text-foreground-muted mt-1">{t("boundary_message")}</p>
          <button onClick={reset} type="button" className="mt-4 px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium">
            {t("refresh_page")}
          </button>
        </div>
      </body>
    </html>
  );
}
