import { render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";
import WorkspaceLayout from "../layout";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: pushMock }) }));

const initAuthMock = vi.fn().mockResolvedValue(undefined);
const ensureUserRoleMock = vi.fn().mockResolvedValue("teacher");
const isAuthenticatedMock = vi.fn().mockReturnValue(true);
const getUserIdMock = vi.fn().mockReturnValue("user-1");
vi.mock("@/lib/auth", () => ({
  initAuth: () => initAuthMock(),
  ensureUserRole: () => ensureUserRoleMock(),
  isAuthenticated: () => isAuthenticatedMock(),
  getUserId: () => getUserIdMock(),
}));

const fetchWithAuthMock = vi.fn();
vi.mock("@/lib/fetchWithAuth", () => ({
  fetchWithAuth: (...args: unknown[]) => fetchWithAuthMock(...args),
}));

vi.mock("@/components/dashboard-v2", () => ({
  DashboardSkeleton: () => <div>skeleton</div>,
}));

const messages = {
  workspace: {
    active_workspace: "Active Workspace",
    no_active_workspace: "No active workspace",
    no_workspaces: "No workspaces found",
    seed_create: "Create",
  },
};

const renderLayout = () =>
  render(
    <NextIntlClientProvider locale="en" messages={messages}>
      <WorkspaceLayout>
        <div>page content</div>
      </WorkspaceLayout>
    </NextIntlClientProvider>,
  );

describe("WorkspaceLayout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    initAuthMock.mockResolvedValue(undefined);
    getUserIdMock.mockReturnValue("user-1");
  });

  it("refreshes the user id via initAuth before fetching workspaces", async () => {
    fetchWithAuthMock.mockResolvedValue({
      json: async () => [{ id: "ws-1", name: "Grade 10 Biology", description: "" }],
    });

    renderLayout();

    const matches = await screen.findAllByText("Grade 10 Biology");
    expect(matches.length).toBeGreaterThan(0);
    expect(initAuthMock).toHaveBeenCalled();
    await waitFor(() =>
      expect(fetchWithAuthMock).toHaveBeenCalledWith("/api/v1/workspaces?user_id=user-1"),
    );
  });

  it("shows no-active-workspace state when the list is empty", async () => {
    fetchWithAuthMock.mockResolvedValue({ json: async () => [] });

    renderLayout();

    expect(await screen.findByText("No active workspace")).toBeTruthy();
  });
});