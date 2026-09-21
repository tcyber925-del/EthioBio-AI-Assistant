import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CopilotPage from "../page";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: pushMock }) }));

vi.mock("@/lib/auth", () => ({
  isAuthenticated: () => true,
  getUserId: () => "user-1",
}));

const streamFetchMock = vi.fn();
vi.mock("@/lib/fetch", () => ({
  streamFetch: (...args: unknown[]) => streamFetchMock(...args),
}));

vi.mock("@/components/dashboard-v2", () => ({
  DashboardLayout: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("@/components/ModelSelector", () => ({
  default: ({ value, onChange }: { value: string; onChange: (m: string) => void }) => (
    <select
      aria-label="model"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      <option value="">default</option>
      <option value="ollama/gemma4:31b">gemma4</option>
    </select>
  ),
}));

vi.mock("@/components/ui/errors", () => ({
  ErrorAlert: () => <div role="alert">error</div>,
}));

const messages = {
  copilot: {
    title: "Teacher Copilot",
    subtitle: "Ask anything about your class.",
    empty_hint: "Ask about your class's progress or plan a lesson.",
    placeholder: "Ask your copilot…",
    thinking: "Thinking…",
    open_lessons: "Open Lessons",
    open_assessment: "Assessment Studio",
  },
  "v2.nav": { copilot: "Copilot" },
  errors: { retry: "Try again", generic: "Something went wrong" },
};

const renderPage = () =>
  render(
    <NextIntlClientProvider locale="en" messages={messages}>
      <CopilotPage />
    </NextIntlClientProvider>,
  );

describe("CopilotPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    streamFetchMock.mockResolvedValue(undefined);
  });

  it("renders suggested prompts when empty", async () => {
    renderPage();

    expect(await screen.findByText("Who needs attention in my class?")).toBeTruthy();
    expect(screen.getByText("Create a quiz on cell division for grade 10")).toBeTruthy();
  });

  it("sends a message and streams the assistant reply", async () => {
    let callbacks: Record<string, (v?: unknown) => void> = {};
    streamFetchMock.mockImplementation((_url, _body, cb) => {
      callbacks = cb;
      return Promise.resolve();
    });

    renderPage();
    const input = await screen.findByPlaceholderText("Ask your copilot…");
    fireEvent.change(input, { target: { value: "analyze my class" } });
    fireEvent.click(screen.getByRole("button", { name: "" }).closest("button") ?? screen.getByRole("button", { name: "" }));

    await waitFor(() => expect(streamFetchMock).toHaveBeenCalled());
    const [, body] = streamFetchMock.mock.calls[0] as [string, Record<string, unknown>];
    expect(body.message).toBe("analyze my class");

    callbacks.onStatus?.("Analyzing your question...");
    expect(await screen.findByText("Analyzing your question...")).toBeTruthy();

    callbacks.onToken?.("The class is");
    callbacks.onToken?.(" improving.");
    callbacks.onDone?.();
    expect(await screen.findByText("The class is improving.")).toBeTruthy();
  });

  it("includes the selected model in the request body", async () => {
    streamFetchMock.mockResolvedValue(undefined);

    renderPage();
    const modelSelect = await screen.findByLabelText("model");
    fireEvent.change(modelSelect, { target: { value: "ollama/gemma4:31b" } });
    const input = await screen.findByPlaceholderText("Ask your copilot…");
    fireEvent.change(input, { target: { value: "who needs attention" } });
    fireEvent.submit(input.closest("form") as HTMLFormElement);

    await waitFor(() => expect(streamFetchMock).toHaveBeenCalled());
    const [, body] = streamFetchMock.mock.calls[0] as [string, Record<string, unknown>];
    expect(body.model).toBe("ollama/gemma4:31b");
  });
});