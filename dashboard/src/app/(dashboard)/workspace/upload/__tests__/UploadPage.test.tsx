import { fireEvent, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";
import UploadPage from "../page";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: pushMock }) }));

const workspaceValue: {
  activeWorkspace: { id: string; name: string } | null;
} = { activeWorkspace: null };
vi.mock("../../context", () => ({
  useWorkspace: () => ({
    workspaces: workspaceValue.activeWorkspace ? [workspaceValue.activeWorkspace] : [],
    activeWorkspace: workspaceValue.activeWorkspace,
    setActiveWorkspace: vi.fn(),
    refreshWorkspaces: vi.fn(),
  }),
}));

vi.mock("@/components/dashboard-v2", () => ({
  DashboardLayout: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("@/lib/auth", () => ({
  getUserId: () => "user-123",
  getToken: () => "token",
}));

const messages = {
  workspace: {
    crumb_workspace: "Workspace",
    crumb_upload: "Upload",
    upload_title: "Upload Assets",
    upload_subtitle: "Ingest educational PDFs into the knowledge gateway.",
    upload_success: "File uploaded successfully!",
    file_selected_hint: "{size} MB selected",
    dropzone_title: "Click to upload or drag & drop",
    dropzone_hint: "Supports PDF, TXT, or MD",
    field_asset_title: "Asset title",
    asset_title_placeholder: "Enter a title",
    submit_ingestion: "Submit for ingestion",
    ingesting: "Ingesting…",
    no_workspace_upload_hint: "You need an active workspace to upload files. Create one from your classroom first.",
    go_to_classroom: "Go to classroom",
  },
  errors: {
    retry: "Try again",
    generic: "Something went wrong",
  },
};

const renderPage = () =>
  render(
    <NextIntlClientProvider locale="en" messages={messages}>
      <UploadPage />
    </NextIntlClientProvider>,
  );

const selectFile = () => {
  const input = screen.getByRole("textbox") as HTMLInputElement;
  fireEvent.change(input, { target: { value: "" } });
  const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
  fireEvent.change(fileInput, {
    target: { files: [new File(["content"], "lesson.pdf", { type: "application/pdf" })] },
  });
};

describe("UploadPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    workspaceValue.activeWorkspace = null;
  });

  it("shows a create-workspace notice and disables submit when there is no active workspace", () => {
    renderPage();

    expect(screen.getByText("You need an active workspace to upload files. Create one from your classroom first.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Go to classroom" })).toBeTruthy();

    selectFile();
    const submit = screen.getByRole("button", { name: "Submit for ingestion" });
    expect(submit.hasAttribute("disabled")).toBe(true);
  });

  it("enables submit after selecting a file when a workspace is active", () => {
    workspaceValue.activeWorkspace = { id: "ws-1", name: "Grade 10 Biology" };
    renderPage();

    expect(screen.queryByText("You need an active workspace to upload files. Create one from your classroom first.")).toBeNull();

    selectFile();
    const submit = screen.getByRole("button", { name: "Submit for ingestion" });
    expect(submit.hasAttribute("disabled")).toBe(false);
  });
});