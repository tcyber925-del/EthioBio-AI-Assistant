import { render, screen } from "@testing-library/react";
import { InsightCard } from "../InsightCard";
import { describe, it, expect } from "vitest";

describe("InsightCard", () => {
  it("renders title and value", () => {
    render(<InsightCard title="Students" value="42" />);
    expect(screen.getByText("Students")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders trend indicator with up direction", () => {
    render(
      <InsightCard
        title="Enrollment"
        value="120"
        trend={{ direction: "up", label: "+12% this week" }}
      />
    );
    expect(screen.getByText("+12% this week")).toBeInTheDocument();
  });

  it("renders trend indicator with down direction", () => {
    render(
      <InsightCard
        title="Dropouts"
        value="3"
        trend={{ direction: "down", label: "-2 from last month" }}
      />
    );
    expect(screen.getByText("-2 from last month")).toBeInTheDocument();
  });

  it("renders context text when provided", () => {
    render(
      <InsightCard
        title="Students"
        value="120"
        context="Across 4 classrooms"
      />
    );
    expect(screen.getByText("Across 4 classrooms")).toBeInTheDocument();
  });
});
