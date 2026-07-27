import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const refresh = vi.fn();
const getUserId = vi.fn<() => string | null>(() => null);
const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
  usePathname: () => "/student",
}));
vi.mock("next-intl", () => ({
  useLocale: () => "en",
  useTranslations: () => (key: string) => key,
}));
vi.mock("@/lib/auth", () => ({
  getUserId: () => getUserId(),
}));
vi.stubGlobal("fetch", fetchMock);

import LanguageSwitcher from "../LanguageSwitcher";

describe("LanguageSwitcher", () => {
  beforeEach(() => {
    refresh.mockClear();
    fetchMock.mockClear();
    getUserId.mockReturnValue(null);
    Object.defineProperty(document, "cookie", {
      writable: true,
      value: "",
    });
  });

  it("renders both locales in select variant", () => {
    render(<LanguageSwitcher variant="select" />);
    const select = screen.getByRole("combobox");
    expect(select).toHaveValue("en");
    expect(screen.getByRole("option", { name: "english" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "amharic" })).toBeInTheDocument();
  });

  it("writes NEXT_LOCALE cookie and refreshes the router on change", () => {
    render(<LanguageSwitcher variant="select" />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "am" } });
    expect(document.cookie).toContain("NEXT_LOCALE=am");
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it("persists the preference to the backend when authenticated", () => {
    getUserId.mockReturnValue("user-42");
    render(<LanguageSwitcher variant="select" />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "am" } });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/users/user-42/language?language=am",
      expect.objectContaining({ method: "PATCH" }),
    );
  });

  it("skips the backend call when unauthenticated", () => {
    render(<LanguageSwitcher variant="select" />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "am" } });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("renders a toggle variant that switches locale on click", () => {
    render(<LanguageSwitcher variant="toggle" />);
    fireEvent.click(screen.getByRole("button", { name: "amharic" }));
    expect(document.cookie).toContain("NEXT_LOCALE=am");
    expect(refresh).toHaveBeenCalledTimes(1);
  });
});
