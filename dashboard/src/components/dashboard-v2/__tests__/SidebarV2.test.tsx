import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";
import { SidebarV2 } from "../SidebarV2";

const en = JSON.parse(
  readFileSync(path.resolve(__dirname, "../../../../messages/en.json"), "utf-8"),
);
const am = JSON.parse(
  readFileSync(path.resolve(__dirname, "../../../../messages/am.json"), "utf-8"),
);

vi.mock("next/navigation", () => ({
  usePathname: () => "/v2/overview",
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("@/lib/auth", () => ({
  getUserRole: () => "student",
  getUserId: () => null,
  isAuthenticated: () => true,
  clearToken: vi.fn(),
}));

vi.mock("@/lib/cookies", () => ({
  setCookie: vi.fn(),
}));

function renderSidebar(messages: Record<string, unknown>, locale: string) {
  return render(
    <NextIntlClientProvider locale={locale} messages={messages}>
      <SidebarV2 />
    </NextIntlClientProvider>,
  );
}

describe("SidebarV2", () => {
  it("renders navigation items for student role", () => {
    renderSidebar(en, "en");
    expect(screen.getByText("Overview")).toBeInTheDocument();
    expect(screen.getByText("Ask Q&A")).toBeInTheDocument();
  });

  it("renders collapse toggle button", () => {
    renderSidebar(en, "en");
    expect(screen.getByLabelText("Collapse sidebar")).toBeInTheDocument();
  });

  it("renders Amharic navigation when locale is am", () => {
    renderSidebar(am, "am");
    expect(screen.getByText("አጠቃላይ እይታ")).toBeInTheDocument();
    expect(screen.getByText("ጥያቄ ጠይቅ")).toBeInTheDocument();
  });
});
