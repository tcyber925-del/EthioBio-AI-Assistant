import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CopyButton } from "../CopyButton";

const messages = {
  common: {
    copy: "Copy",
    copied: "Copied",
  },
};

const writeText = vi.fn().mockResolvedValue(undefined);

beforeEach(() => {
  Object.defineProperty(navigator, "clipboard", {
    value: { writeText },
    configurable: true,
  });
  writeText.mockClear();
});

afterEach(() => {
  vi.useRealTimers();
});

function renderButton() {
  return render(
    <NextIntlClientProvider locale="en" messages={messages}>
      <CopyButton text="hello" />
    </NextIntlClientProvider>,
  );
}

describe("CopyButton", () => {
  it("copies the text to the clipboard on click", async () => {
    renderButton();
    fireEvent.click(screen.getByRole("button", { name: "Copy" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith("hello"));
  });

  it("shows a copied state after copying", async () => {
    renderButton();
    fireEvent.click(screen.getByRole("button", { name: "Copy" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Copied" })).toBeInTheDocument(),
    );
  });

  it("reverts to the copy state after 2 seconds", async () => {
    vi.useFakeTimers();
    renderButton();
    fireEvent.click(screen.getByRole("button", { name: "Copy" }));
    await act(async () => {});
    expect(screen.getByRole("button", { name: "Copied" })).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(2000));
    expect(screen.getByRole("button", { name: "Copy" })).toBeInTheDocument();
  });
});