import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { readFileSync } from "node:fs";
import path from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { StudentDashboard } from "../StudentDashboard";

const en = JSON.parse(
  readFileSync(path.resolve(__dirname, "../../../../../messages/en.json"), "utf-8"),
);
const am = JSON.parse(
  readFileSync(path.resolve(__dirname, "../../../../../messages/am.json"), "utf-8"),
);

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/v2/overview",
}));
vi.mock("@/lib/auth", () => ({
  getUserId: () => null,
}));
vi.mock("@/lib/fetchWithAuth", () => ({
  fetchWithAuth: vi.fn(),
}));
vi.mock("@/components/misconceptions/MisconceptionPanel", () => ({
  MisconceptionPanel: () => null,
}));

import { fetchWithAuth } from "@/lib/fetchWithAuth";

const STUDENT_DATA = {
  user: { id: "u1", email: "abebe@school.edu", grade_level: 9, created_at: null },
  gamification: {
    total_xp: 120,
    level: 2,
    current_streak: 4,
    longest_streak: 7,
    next_level_xp: 200,
    achievements: [
      { id: "a1", title: "First Steps", description: "", icon: "", unlocked_at: "2026-01-01" },
    ],
  },
  readiness: {
    overall_readiness: 62,
    readiness_band: "ready",
    topic_readiness: { Photosynthesis: 80, "Cell Structure": 45 },
  },
  weak_topics: [
    {
      topic: "Cell Structure",
      severity: "moderate",
      average_score: 45,
      attempt_count: 3,
      misconceptions: [],
    },
  ],
  due_reviews: [
    { topic: "Cell Structure", next_review_at: "2026-07-27", mastery_score: 0.4, interval_days: 2 },
    { topic: "Photosynthesis", next_review_at: "2026-07-28", mastery_score: 0.7, interval_days: 4 },
  ],
  recent_activity: [],
};

function renderDashboard(messages: Record<string, unknown>, locale: string) {
  return render(
    <NextIntlClientProvider locale={locale} messages={messages}>
      <StudentDashboard />
    </NextIntlClientProvider>,
  );
}

describe("StudentDashboard", () => {
  beforeEach(() => {
    vi.mocked(fetchWithAuth).mockResolvedValue({
      json: () => Promise.resolve(STUDENT_DATA),
    } as Response);
  });

  it("renders hero, metrics and section titles in English", async () => {
    renderDashboard(en, "en");
    expect(await screen.findByText("Welcome back, abebe")).toBeInTheDocument();
    expect(screen.getByText("Readiness")).toBeInTheDocument();
    expect(screen.getByText("Weekly Progress")).toBeInTheDocument();
    expect(screen.getByText("Topic Mastery")).toBeInTheDocument();
    expect(screen.getByText("Achievements")).toBeInTheDocument();
    expect(screen.getByText(/2 reviews\*\* due/)).toBeInTheDocument();
  });

  it("renders Amharic when locale is am", async () => {
    renderDashboard(am, "am");
    expect(
      await screen.findByText("እንኳን በደህና ተመለሱ፣ abebe"),
    ).toBeInTheDocument();
    expect(screen.getByText("ዝግጁነት")).toBeInTheDocument();
    expect(screen.getByText("ሳምንታዊ እድገት")).toBeInTheDocument();
    expect(screen.getByText("ስኬቶች")).toBeInTheDocument();
  });
});
