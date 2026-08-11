import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";
import { ErrorBanner } from "../ErrorBanner";

const messages = {
  errors: { generic: "Something went wrong. Please try again." },
  common: { retry: "Retry" },
};

function renderBanner(props: React.ComponentProps<typeof ErrorBanner>) {
  return render(
    <NextIntlClientProvider locale="en" messages={messages}>
      <ErrorBanner {...props} />
    </NextIntlClientProvider>,
  );
}

describe("ErrorBanner", () => {
  it("renders the catalog message", () => {
    renderBanner({ error: { category: "unknown", retryable: false } });
    expect(screen.getByText("Something went wrong. Please try again.")).toBeInTheDocument();
  });
  it("shows the default retry label when action supplied without actionLabel", () => {
    renderBanner({ error: { category: "unknown", retryable: false }, onAction: () => {} });
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
  it("uses the actionLabel override when supplied", () => {
    renderBanner({ error: { category: "unknown", retryable: false }, onAction: () => {}, actionLabel: "View details" });
    expect(screen.getByRole("button", { name: "View details" })).toBeInTheDocument();
  });
  it("hides the button when no onAction", () => {
    renderBanner({ error: { category: "unknown", retryable: false } });
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
