# PRD — EthioBio Dashboard Redesign

## Project: EthioBio AI Assistant

## Status: Approved for Implementation

## Priority: CRITICAL

## Type: Platform-Wide UX/UI Redesign

---

# 1. Executive Summary

The current dashboard functions correctly but resembles a generic SaaS/admin template. The redesign must transform EthioBio into a premium educational platform with a modern, minimalist, and highly intentional design language.

The redesign must NOT look like:

* AI-generated dashboards
* Bootstrap admin panels
* Generic analytics tools
* Color-heavy SaaS templates
* Enterprise CRUD systems

The redesign SHOULD feel inspired by:

* Linear
* Notion
* Arc Browser
* Stripe Dashboard
* Khan Academy
* Duolingo (without gamification excess)

Core philosophy:

> Calm Educational Intelligence

The platform should feel like a modern learning workspace where insights matter more than raw statistics.

---

# 2. Redesign Objectives

## Primary Goals

### Goal 1

Create a premium educational platform aesthetic.

### Goal 2

Reduce visual clutter by 50%+.

### Goal 3

Replace database-centric metrics with learning-centric insights.

### Goal 4

Improve information hierarchy.

### Goal 5

Create a memorable visual identity unique to EthioBio.

---

# 3. Design Principles

All dashboard pages MUST follow:

### Principle 1: Content First

UI exists to support learning.

Never decorate for decoration's sake.

### Principle 2: Fewer Cards

Avoid card explosions.

Group related information.

### Principle 3: Neutral First

90% neutral surfaces.

10% accent colors.

### Principle 4: Breathing Room

Generous whitespace.

### Principle 5: Insight Over Metrics

Replace:

* User count
* Quiz count
* Lesson count

With:

* Learning health
* Engagement
* Progress
* Mastery

### Principle 6: Human-Centered

The dashboard should feel personal.

Every role should immediately understand:

* What matters
* What needs attention
* What to do next

---

# 4. New Design Language

## Typography

Create a new typography scale.

### Display

Used only for major dashboard hero sections.

```css
font-size: 36px;
font-weight: 700;
line-height: 1.1;
```

### Heading

```css
font-size: 24px;
font-weight: 600;
```

### Subheading

```css
font-size: 18px;
font-weight: 600;
```

### Body

```css
font-size: 14px;
font-weight: 400;
```

### Caption

```css
font-size: 12px;
font-weight: 500;
```

---

# 5. Color System

## Remove Rainbow Dashboard

Current color diversity must be eliminated.

---

## Core Palette

### Background

```css
#FAFAFA
```

### Surface

```css
#FFFFFF
```

### Primary Text

```css
#0F172A
```

### Secondary Text

```css
#64748B
```

### Borders

```css
#E5E7EB
```

---

## Accent Palette

### EthioBio Accent

```css
#14B8A6
```

Used for:

* Active states
* Progress
* Selected navigation
* Key CTAs

---

## Semantic Colors

### Success

```css
#22C55E
```

### Warning

```css
#F59E0B
```

### Error

```css
#EF4444
```

Use sparingly.

---

# 6. Layout Architecture

## New Dashboard Structure

Current:

```text
Sidebar
Content
```

Replace with:

```text
Sidebar
│
├── Context Header
│
├── Main Canvas
│
└── Activity Rail (optional)
```

---

# 7. Sidebar Redesign

## Requirements

### Keep Width

Expanded:

```css
256px
```

Collapsed:

```css
72px
```

---

### Structure

```text
EthioBio

Overview

Learning
 ├ Lessons
 ├ Students
 ├ Quizzes

AI Tools
 ├ Tutor
 ├ Diagram Studio

Analytics

Settings
```

---

### Features

Required:

* Collapse support
* Smooth animations
* Active route indicator
* Search navigation
* Keyboard shortcuts

---

# 8. Global Dashboard Hero

Every dashboard MUST start with a hero section.

---

## Student Example

```text
Welcome Back, Sarah

You are 82% through Biology Fundamentals

Continue Learning
```

---

## Teacher Example

```text
Teaching Command Center

23 students active today

4 students need intervention
```

---

## Parent Example

```text
Your Child's Learning Journey

Progress this week:
+12%
```

---

## Admin Example

```text
Platform Overview

Healthy system status

1,240 active learners
```

---

# 9. New Component Library

## Component: InsightCard

Replace StatCard entirely.

---

### Structure

```text
Title

Primary Value

Trend

Context
```

Example:

```text
Learning Health

87%

+12%

Compared to last week
```

---

## Component: MetricStrip

Horizontal summary metrics.

Example:

```text
89% Readiness
12 Active Lessons
4 Intervention Alerts
```

Single surface.

Not multiple cards.

---

## Component: ActivityTimeline

Replace most activity tables.

Structure:

```text
● Sarah completed Cell Biology Quiz

● David unlocked Genetics Badge

● AI generated study plan

● Teacher published assignment
```

---

## Component: LearningProgress

Visual progress component.

Features:

* Milestones
* Completion
* Learning path position

---

## Component: AIInsightPanel

Displays AI-generated recommendations.

Example:

```text
Students struggle most with Photosynthesis.

Recommendation:
Review Chapter 4.
```

---

# 10. Dashboard-Specific Redesigns

## Student Dashboard

### Section 1

Hero

### Section 2

Continue Learning

Largest card.

### Section 3

Weekly Progress

### Section 4

Achievements

### Section 5

Recent Activity

### Section 6

AI Recommendations

---

## Teacher Dashboard

### Section 1

Teaching Command Center

### Section 2

Class Health

### Section 3

Students Needing Attention

### Section 4

Upcoming Tasks

### Section 5

AI Teaching Insights

### Section 6

Recent Class Activity

---

## Parent Dashboard

### Section 1

Child Overview

### Section 2

Growth Trend

### Section 3

Strength Areas

### Section 4

Improvement Areas

### Section 5

Weekly AI Summary

---

## School Dashboard

### Section 1

School Health Score

### Section 2

Class Performance Trends

### Section 3

Teacher Activity

### Section 4

Risk Detection

### Section 5

AI Recommendations

---

## Admin Dashboard

### Section 1

Platform Health

### Section 2

Usage Trends

### Section 3

System Events

### Section 4

AI Infrastructure Metrics

### Section 5

Recent Platform Activity

---

# 11. Data Visualization Redesign

## Current State

Too many charts and tables.

---

## Required Changes

### Use

* Sparklines
* Trend indicators
* Progress bars
* Timelines

### Avoid

* Pie charts
* Multi-color charts
* 3D charts
* Decorative graphs

---

# 12. Card System Redesign

## Card Style

```css
border-radius: 20px;
```

---

## Shadows

```css
0 1px 2px rgba(0,0,0,.04),
0 12px 32px rgba(0,0,0,.06)
```

---

## Borders

Extremely subtle.

---

## Internal Padding

```css
24px
```

minimum.

---

# 13. Animation System

Implement Framer Motion.

---

## Required Animations

### Page Transitions

200ms

### Sidebar Expand

200ms

### Card Reveal

150ms

### Activity Updates

150ms

---

## Rules

No bounce.

No exaggerated motion.

No gimmicks.

---

# 14. Educational Identity Layer

This creates differentiation.

---

## Subtle Biology Themes

Use:

* DNA-inspired geometry
* Cell-inspired shapes
* Molecular grid motifs

Opacity:

```css
3-5%
```

maximum.

---

## Achievement Icons

Replace generic trophies.

Use:

* Microscope
* DNA
* Neuron
* Cell
* Leaf
* Genome

---

# 15. Accessibility Requirements

Must achieve:

### WCAG AA

Required.

---

### Keyboard Navigation

Required.

---

### Screen Reader Support

Required.

---

### High Contrast Mode

Required.

---

# 16. Responsive Requirements

Support:

### Desktop

1440+

### Laptop

1024+

### Tablet

768+

### Mobile

375+

---

# 17. Technical Refactor

## Create

```text
src/components/dashboard-v2/
```

Structure:

```text
dashboard-v2/
├ HeroSection
├ InsightCard
├ ActivityTimeline
├ AIInsightPanel
├ LearningProgress
├ MetricStrip
├ DashboardLayout
├ ContextHeader
├ SidebarV2
```

---

## New Design Tokens

Create:

```text
src/styles/design-system.ts
```

Contains:

* colors
* typography
* spacing
* shadows
* radii
* motion

---

# 18. Implementation Phases

## Phase 1

Foundation

* New design tokens
* Typography
* Colors
* Layout system
* Sidebar

Priority:
CRITICAL

---

## Phase 2

Core Components

* InsightCard
* HeroSection
* Timeline
* AIInsightPanel

Priority:
CRITICAL

---

## Phase 3

Role Dashboards

* Student
* Teacher
* Parent
* School
* Admin

Priority:
CRITICAL

---

## Phase 4

Animations

* Framer Motion
* Page transitions
* Loading states

Priority:
HIGH

---

## Phase 5

Educational Identity

* Biology visual language
* Achievement redesign
* Branding refinement

Priority:
HIGH

---

# 19. Success Criteria

The redesign is considered successful when:

* Dashboard no longer resembles a generic SaaS admin template.
* Visual clutter reduced by at least 50%.
* User attention is directed to insights rather than counts.
* Every role immediately understands next actions.
* Platform feels premium and educational.
* Interface remains fast and accessible.
* Design language is cohesive across all dashboard experiences.
* Dashboard feels handcrafted rather than AI-generated.

---

# 20. Final Implementation Directive

When making design decisions:

DO NOT ask:

> "How do most dashboards look?"

Instead ask:

> "How would a world-class educational intelligence platform look if designed by the teams behind Linear, Notion, and Khan Academy?"

Every implementation decision must reinforce calmness, clarity, educational focus, and premium craftsmanship.
