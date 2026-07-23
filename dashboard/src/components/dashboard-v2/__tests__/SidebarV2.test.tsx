import { render, screen } from "@testing-library/react";
import { SidebarV2 } from "../SidebarV2";
import { describe, it, expect, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/v2/overview",
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("next-intl", () => ({
  useLocale: () => "en",
}));

vi.mock("@/lib/auth", () => ({
  getUserRole: () => "student",
  isAuthenticated: () => true,
  clearToken: vi.fn(),
}));

vi.mock("@/lib/cookies", () => ({
  setCookie: vi.fn(),
}));

describe("SidebarV2", () => {
  it("renders navigation items for student role", () => {
    render(<SidebarV2 />);
    expect(screen.getByText("Overview")).toBeInTheDocument();
    expect(screen.getByText("Ask Q&A")).toBeInTheDocument();
  });

  it("renders collapse toggle button", () => {
    render(<SidebarV2 />);
    expect(screen.getByLabelText("Collapse sidebar")).toBeInTheDocument();
  });
});
