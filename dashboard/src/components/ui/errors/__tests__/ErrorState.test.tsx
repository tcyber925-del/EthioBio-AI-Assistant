import { fireEvent, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";
import { ErrorState } from "../ErrorState";

const messages = {
  errors: {
    generic: "Something went wrong. Please try again.",
    http: { "500": "Something went wrong. Please try again." },
  },
  common: { retry: "Retry" },
};

function renderState(props: React.ComponentProps<typeof ErrorState>) {
  return render(
    <NextIntlClientProvider locale="en" messages={messages}>
      <ErrorState {...props} />
    </NextIntlClientProvider>,
  );
}

describe("ErrorState", () => {
  it("shows message and retry for retryable errors", () => {
    const onRetry = vi.fn();
    renderState({ error: { category: "server", status: 500, retryable: true }, onRetry });
    expect(screen.getByText("Something went wrong. Please try again.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalled();
  });
  it("hides retry for non-retryable errors", () => {
    renderState({ error: { category: "not_found", status: 404, retryable: false }, onRetry: () => {} });
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
  });
  it("supports an explicit title override", () => {
    renderState({ error: { category: "server", retryable: false }, title: "Couldn't load students", onRetry: () => {} });
    expect(screen.getByText("Couldn't load students")).toBeInTheDocument();
  });
});
