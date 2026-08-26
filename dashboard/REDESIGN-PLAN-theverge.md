# Dashboard Redesign Plan: Verge-Inspired Editorial System

## Objective

Redesign the EthioSci dashboard around the visual system in `dashboard/DESIGN-theverge.md`: dark editorial canvas, high-contrast saturated blocks, mono-uppercase metadata, hairline borders, and a StoryStream-style activity rhythm.

The redesign should keep the dashboard usable as an education operations product. Use the Verge influence as a system language, not as a literal clone.

## Current State

- `dashboard/src/components/dashboard-v2/` is the best migration target. It already centralizes the active overview dashboard through `DashboardLayout`, `SidebarV2`, `HeroSection`, `MetricStrip`, `ActivityTimeline`, `LearningProgress`, and role-specific dashboards.
- Current v2 tokens are light SaaS tokens in `dashboard/src/styles/design-system.ts` and duplicated as CSS variables in `dashboard/src/app/globals.css`.
- The root dashboard still has older components and routes. Avoid redesigning every route at once.
- The most valuable first surface is `/v2/overview`, because it composes student, parent, teacher, school, and admin dashboards through one layout.

## Design Translation

### Brand Tokens

Replace v2 light tokens with Verge-inspired dashboard tokens:

- Canvas: `#131313`
- Surface slate: `#2d2d2d`
- Primary text: `#ffffff`
- Secondary text: `#949494`
- Mint accent: `#3cffd0`
- Ultraviolet accent: `#5200ff`
- Mint border: `#309875`
- Purple rule: `#3d00bf`
- Link hover: `#3860be`
- Focus cyan: `#1eaedb`

Keep semantic status colors legible, but tune them to the dark system instead of relying on the current soft Tailwind washes.

### Typography

Do not add proprietary fonts. Use fallbacks:

- Display: `Impact`, `Arial Black`, `Helvetica Neue Condensed`, `Helvetica`, `sans-serif`
- UI: `Inter`, `Helvetica`, `Arial`, `sans-serif`
- Mono labels: `JetBrains Mono`, `Space Mono`, `Courier New`, `monospace`

Create utility classes for:

- `verge-display`: large compressed display headings, 60px+ only on true hero/masthead moments.
- `verge-label`: mono uppercase labels, timestamps, category tags, button text.
- `verge-body`: readable dashboard body text.

Use the huge display style sparingly. Dashboards need scan density; most operational panels should stay in the 12-24px range.

### Component Rules

- Replace soft shadows with 1px borders.
- Use saturated accent fills for high-priority cards only.
- Standard tiles use `20px` radius; feature panels use `24px`; inputs use `2px`.
- Hover states should change text/border color, not lift or scale cards.
- Buttons become mint pills, slate pills, or outlined mint pills.
- Activity feeds should become StoryStream-like timelines with a left rail, mono timestamps, and pill cards.

## Implementation Phases

### Phase 1: Token Cutover

Files:

- `dashboard/src/app/globals.css`
- `dashboard/src/styles/design-system.ts`
- `dashboard/tailwind.config.js`

Work:

- Replace `--v2-*` variables with the dark editorial palette.
- Add any missing variables for purple rule, focus cyan, link hover, inverted text, and image frame.
- Update `design-system.ts` so component imports and inline style helpers use the same values as CSS variables.
- Extend Tailwind colors for `v2-purple`, `v2-link-hover`, `v2-focus`, and `v2-inverted`.
- Remove v2 shadow reliance from tokens or redefine shadows as hairline border/ring treatments.

Acceptance:

- `/v2/overview` renders dark by changing tokens alone.
- No white-on-white or black-on-dark text regressions.
- `npx tsc --noEmit` passes in `dashboard/`.

### Phase 2: Layout And Navigation

Files:

- `dashboard/src/components/dashboard-v2/DashboardLayout.tsx`
- `dashboard/src/components/dashboard-v2/SidebarV2.tsx`
- `dashboard/src/components/dashboard-v2/ContextHeader.tsx`
- `dashboard/src/components/dashboard-v2/DashboardSkeleton.tsx`
- `dashboard/src/components/dashboard-v2/BioPattern.tsx`

Work:

- Convert the layout to a dark canvas with a thin bordered sidebar.
- Replace the light science-themed background wash with either no background pattern or a very subtle mono-line motif.
- Change the sidebar logo area into a compact masthead: large `EthioSci` wordmark when expanded, icon-only when collapsed.
- Make nav labels mono-uppercase.
- Use mint underline or left border for active state.
- Keep search overlay, language selector, logout, and collapse behavior intact.

Acceptance:

- Sidebar works expanded and collapsed.
- Search overlay remains keyboard accessible.
- Active nav is visible in dark mode.
- Mobile/narrow widths do not clip text.

### Phase 3: Shared Dashboard Components

Files:

- `dashboard/src/components/dashboard-v2/HeroSection.tsx`
- `dashboard/src/components/dashboard-v2/MetricStrip.tsx`
- `dashboard/src/components/dashboard-v2/InsightCard.tsx`
- `dashboard/src/components/dashboard-v2/AIInsightPanel.tsx`
- `dashboard/src/components/dashboard-v2/LearningProgress.tsx`
- `dashboard/src/components/dashboard-v2/ActivityTimeline.tsx`

Work:

- Turn `HeroSection` into an editorial masthead: large display title, mono subtitle/status line, mint pill action.
- Convert `MetricStrip` from a white shadow card into a bordered row of metric tiles. Let the first/high-priority metric use mint or ultraviolet fill.
- Convert `ActivityTimeline` into the StoryStream pattern from the brief: rail, mono timestamp, pill-cornered entries, occasional accent tile by activity type.
- Convert insight and progress panels into flat bordered/slate surfaces with strong labels and restrained accent fills.
- Keep dashboard controls stable in size to avoid layout shift.

Acceptance:

- Student dashboard has a clear first-viewport signal: masthead, primary next action, and metrics.
- Timeline reads as a distinct visual motif.
- Components remain reusable by all role dashboards.

### Phase 4: Role Dashboard Adaptation

Files:

- `dashboard/src/components/dashboard-v2/dashboards/StudentDashboard.tsx`
- `dashboard/src/components/dashboard-v2/dashboards/TeacherDashboard.tsx`
- `dashboard/src/components/dashboard-v2/dashboards/ParentDashboard.tsx`
- `dashboard/src/components/dashboard-v2/dashboards/SchoolDashboard.tsx`
- `dashboard/src/components/dashboard-v2/dashboards/AdminDashboard.tsx`

Work:

- Replace repeated inline card class strings with shared Verge-style panel classes or small local helpers.
- Use saturated blocks only for high-priority states:
  - Student: next review / weakest topic.
  - Teacher: attention-needed class or misconception cluster.
  - Parent: child needing support.
  - School/admin: review queue, system risk, or adoption trend.
- Keep operational tables and dense lists quieter: slate background, white/mint hairline border, mono labels.
- Remove emoji status markers in favor of icon + mono label treatments where practical.

Acceptance:

- All role dashboards render consistently through `DashboardLayout`.
- No role dashboard depends on the old light `v2` surface assumptions.
- Data-empty, loading, and error states match the new system.

### Phase 5: Legacy Surface Alignment

Files to evaluate after v2 is stable:

- `dashboard/src/app/page.tsx`
- `dashboard/src/app/student/page.tsx`
- `dashboard/src/app/recovery/page.tsx`
- `dashboard/src/app/parent/page.tsx`
- `dashboard/src/app/school/page.tsx`
- `dashboard/src/app/admin/**`
- `dashboard/src/components/ui/*`
- `dashboard/src/components/gamification/*`
- `dashboard/src/components/recovery/*`

Work:

- Decide whether each legacy page should migrate into `DashboardLayout` or receive a minimal token-compatible retheme.
- Retheme shared `ui` components only after identifying active usage.
- Convert gamification and recovery widgets to the same card, label, button, and timeline rules.
- Avoid redesigning specialized tools like SVG editor or diagrams until the shell and dashboard surfaces are stable.

Acceptance:

- Top navigation paths do not visually jump between incompatible themes.
- Recovery/gamification widgets can be embedded in the v2 dashboard without looking foreign.

### Phase 6: Responsive And Accessibility Pass

Work:

- Verify desktop, tablet, and mobile widths.
- Ensure display headings clamp gracefully without viewport-based font scaling.
- Check contrast for mint, ultraviolet, warning, and error states.
- Ensure focus states use `#1eaedb` and are visible on all controls.
- Confirm keyboard search, sidebar collapse, language selector, and logout are reachable.
- Respect `prefers-reduced-motion`.

Acceptance:

- No text overlap or clipped controls at common widths.
- All interactive elements have visible focus states.
- Motion remains subtle and disabled when requested.

## Verification

Run from `dashboard/`:

```bash
npx tsc --noEmit
npm run build
```

Manual/browser checks:

- Start with `npm run dev`.
- Verify `/v2/overview` for each role state available locally.
- Capture desktop and mobile screenshots.
- Check sidebar expanded/collapsed.
- Check search overlay with keyboard.
- Check loading, empty, and error states where they can be forced.

## Suggested First Commit

Scope the first implementation commit to:

- `globals.css`
- `design-system.ts`
- `tailwind.config.js`
- `DashboardLayout.tsx`
- `SidebarV2.tsx`
- `HeroSection.tsx`
- `MetricStrip.tsx`
- `ActivityTimeline.tsx`

This creates the visual foundation and proves the StoryStream direction before touching every role dashboard.
