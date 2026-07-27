import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";
import RecoveryProgressCard from "../RecoveryProgressCard";

// Real next-intl provider with ICU plural messages — no _plural twin keys.
const messages = {
  gamification: {
    recovery_progress: "Recovery Progress",
    no_recovery_plans: "No Recovery Plans",
    recovery_desc: "Complete quizzes to identify weak areas.",
    tasks_progress: "{completed}/{total} tasks",
    active_plans_count:
      "{count, plural, one {# active plan} other {# active plans}}",
    percent_complete: "{pct}% complete",
    tasks_remaining:
      "{count, plural, one {# task remaining} other {# tasks remaining}}",
  },
};

function renderCard(props: {
  activePlans: number;
  totalTasks: number;
  completedTasks: number;
  overallProgressPct: number;
}) {
  return render(
    <NextIntlClientProvider locale="en" messages={messages}>
      <RecoveryProgressCard {...props} />
    </NextIntlClientProvider>,
  );
}

describe("RecoveryProgressCard pluralization", () => {
  it("renders plural forms for counts > 1 via ICU plural", () => {
    renderCard({ activePlans: 2, totalTasks: 5, completedTasks: 2, overallProgressPct: 40 });
    expect(screen.getByText("2 active plans")).toBeInTheDocument();
    expect(screen.getByText("3 tasks remaining")).toBeInTheDocument();
  });

  it("renders singular forms for count = 1 via ICU plural", () => {
    renderCard({ activePlans: 1, totalTasks: 1, completedTasks: 0, overallProgressPct: 0 });
    expect(screen.getByText("1 active plan")).toBeInTheDocument();
    expect(screen.getByText("1 task remaining")).toBeInTheDocument();
  });
});
