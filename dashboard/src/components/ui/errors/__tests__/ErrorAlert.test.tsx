import { fireEvent, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";
import { ErrorAlert } from "../ErrorAlert";

const messages = {
  errors: {
    generic: "Something went wrong. Please try again.",
    retry: "Try again",
    codes: { auth_invalid_credentials: "Invalid email or password. Please check your credentials and try again." },
    http: { "429": "Too many requests. Please try again shortly." },
  },
};

function renderAlert(props: React.ComponentProps<typeof ErrorAlert>) {
  return render(
    <NextIntlClientProvider locale="en" messages={messages}>
      <ErrorAlert {...props} />
    </NextIntlClientProvider>,
  );
}

describe("ErrorAlert", () => {
  it("renders the catalog message for a known code", () => {
    renderAlert({ error: { category: "authentication", code: "auth_invalid_credentials", status: 401, retryable: false } });
    expect(screen.getByText(/Invalid email or password/)).toBeInTheDocument();
  });
  it("renders the generic message for unknown errors", () => {
    renderAlert({ error: { category: "unknown", retryable: false } });
    expect(screen.getByText("Something went wrong. Please try again.")).toBeInTheDocument();
  });
  it("exposes an accessible alert role", () => {
    renderAlert({ error: { category: "unknown", retryable: false } });
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
  it("never renders raw JSON or object", () => {
    renderAlert({ error: { category: "unknown", retryable: false } });
    expect(screen.queryByText("[object Object]")).not.toBeInTheDocument();
  });
  it("fires the retry action when supplied", () => {
    const onRetry = vi.fn();
    renderAlert({ error: { category: "server", status: 500, retryable: true }, onRetry });
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
  it("hides the retry button when not supplied", () => {
    renderAlert({ error: { category: "authentication", status: 401, retryable: false } });
    expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
  });
});
