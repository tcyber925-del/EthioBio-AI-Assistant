import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { readFileSync } from "node:fs";
import path from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ParentDashboard } from "../ParentDashboard";

const en = JSON.parse(
  readFileSync(path.resolve(__dirname, "../../../../../messages/en.json"), "utf-8"),
);

vi.mock("@/lib/fetchWithAuth", () => ({
  fetchWithAuth: vi.fn(),
}));

import { fetchWithAuth } from "@/lib/fetchWithAuth";

const CHILDREN = [
  { student_id: "c1", name: "Abebe", grade_level: 9, last_active: null, overall_readiness: 70 },
  { student_id: "c2", name: "Hanna", grade_level: 7, last_active: null, overall_readiness: 55 },
];

const WEEKLY_SUMMARY = {
  summary_text: "Good progress this week.",
  summary_amharic: null,
  week_start: "2026-08-01",
  week_end: "2026-08-07",
  is_low_performance_warning: false,
};

function renderDashboard() {
  return render(
    <NextIntlClientProvider locale="en" messages={en}>
      <ParentDashboard />
    </NextIntlClientProvider>,
  );
}

describe("ParentDashboard", () => {
  beforeEach(() => {
    vi.mocked(fetchWithAuth).mockReset();
    vi.mocked(fetchWithAuth).mockImplementation((url) => {
      if (url === "/api/parent/children") {
        return Promise.resolve({
          json: () => Promise.resolve({ children: CHILDREN }),
        } as Response);
      }
      return Promise.resolve({
        json: () => Promise.resolve(WEEKLY_SUMMARY),
      } as Response);
    });
  });

  it("keeps the page shell and shows an ErrorBanner when a per-child fetch fails", async () => {
    vi.mocked(fetchWithAuth).mockImplementation((url) => {
      if (url === "/api/parent/children") {
        return Promise.resolve({
          json: () => Promise.resolve({ children: CHILDREN }),
        } as Response);
      }
      if (url.endsWith("/progress")) {
        return Promise.reject(new TypeError("Failed to fetch"));
      }
      return Promise.resolve({
        json: () => Promise.resolve(WEEKLY_SUMMARY),
      } as Response);
    });
    renderDashboard();
    expect(
      await screen.findByText("Your Child's Learning Journey"),
    ).toBeInTheDocument();
    expect(screen.getByRole("combobox")).toBeInTheDocument();
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(
      screen.getByText("Please check your internet connection and try again."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("retries the selected child's progress fetch from the banner", async () => {
    vi.mocked(fetchWithAuth).mockImplementation((url) => {
      if (url === "/api/parent/children") {
        return Promise.resolve({
          json: () => Promise.resolve({ children: CHILDREN }),
        } as Response);
      }
      if (url.endsWith("/progress")) {
        return Promise.reject(new TypeError("Failed to fetch"));
      }
      return Promise.resolve({
        json: () => Promise.resolve(WEEKLY_SUMMARY),
      } as Response);
    });
    renderDashboard();
    await screen.findByRole("alert");
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => {
      const progressCalls = vi.mocked(fetchWithAuth).mock.calls.filter(
        ([url]) => url === "/api/parent/children/c1/progress",
      );
      expect(progressCalls.length).toBe(2);
    });
  });

  it("renders the child's progress when per-child fetches succeed", async () => {
    vi.mocked(fetchWithAuth).mockImplementation((url) => {
      if (url === "/api/parent/children") {
        return Promise.resolve({
          json: () => Promise.resolve({ children: CHILDREN }),
        } as Response);
      }
      if (url.endsWith("/progress")) {
        return Promise.resolve({
          json: () => Promise.resolve({
            student_id: "c1",
            overall_readiness: 70,
            mastery_heatmap: { Photosynthesis: 80 },
            recent_quizzes: [],
            streak: 3,
            total_xp: 240,
          }),
        } as Response);
      }
      return Promise.resolve({
        json: () => Promise.resolve(WEEKLY_SUMMARY),
      } as Response);
    });
    renderDashboard();
    expect(await screen.findByText("Abebe · Grade 9")).toBeInTheDocument();
    expect(screen.getByText("Topic Mastery")).toBeInTheDocument();
    expect(
      screen.queryByRole("alert"),
    ).not.toBeInTheDocument();
  });
});
