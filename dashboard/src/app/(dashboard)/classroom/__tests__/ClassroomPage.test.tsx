import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ClassroomListPage from "../page";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: pushMock }) }));

vi.mock("@/lib/auth", () => ({ isAuthenticated: () => true }));

const fetchWithAuthMock = vi.fn();
const fetchWithAuthJsonMock = vi.fn();
vi.mock("@/lib/fetchWithAuth", () => ({
  fetchWithAuth: (...args: unknown[]) => fetchWithAuthMock(...args),
  fetchWithAuthJson: (...args: unknown[]) => fetchWithAuthJsonMock(...args),
}));

vi.mock("@/components/Skeleton", () => ({
  CardSkeleton: () => <div>skeleton</div>,
}));

vi.mock("@/components/ui/errors", () => ({
  ErrorState: ({ error }: { error: { code?: string } }) => (
    <div role="alert">{error?.code ?? "request-failed"}</div>
  ),
}));

const messages = {
  classroom: {
    title: "Classrooms",
    create: "Create",
    classroom_name_placeholder: "Class name",
    grade: "Grade",
    no_classrooms: "No classrooms yet",
    no_classrooms_subtitle: "Create your first classroom",
    students: "students",
    student_grade: "Grade",
  },
  common: {
    cancel: "Cancel",
    save: "Save",
  },
};

const renderPage = () =>
  render(
    <NextIntlClientProvider locale="en" messages={messages}>
      <ClassroomListPage />
    </NextIntlClientProvider>,
  );

describe("ClassroomListPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchWithAuthJsonMock.mockResolvedValue([]);
  });

  it("renders classrooms returned by the API", async () => {
    fetchWithAuthJsonMock.mockResolvedValue([
      { id: "c1", name: "Grade 10 Bio", grade_level: 10, student_count: 3 },
    ]);

    renderPage();

    expect(await screen.findByText("Grade 10 Bio")).toBeTruthy();
    expect(screen.getByText("3 students")).toBeTruthy();
  });

  it("creates a classroom and seeds its workspace", async () => {
    fetchWithAuthMock.mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({ id: "c1", name: "Grade 10 Bio", grade_level: 10, student_count: 0 }),
    });

    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Create" }));
    fireEvent.change(screen.getByPlaceholderText("Class name"), {
      target: { value: "Grade 10 Bio" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(fetchWithAuthMock).toHaveBeenCalledWith(
        "/teacher/classrooms",
        expect.objectContaining({ method: "POST" }),
      ),
    );
    await waitFor(() =>
      expect(fetchWithAuthMock).toHaveBeenCalledWith(
        "/api/v1/workspaces/seed/c1",
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });

  it("shows an error when classroom creation fails", async () => {
    fetchWithAuthMock.mockResolvedValue({ ok: false, status: 500, text: async () => "" });

    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Create" }));
    fireEvent.change(screen.getByPlaceholderText("Class name"), {
      target: { value: "Grade 10 Bio" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByRole("alert")).toBeTruthy();
  });
});