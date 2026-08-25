# Dashboard Frontend

The Next.js 14 App Router frontend for the EthioSci AI Assistant. Currently undergoing a full visual redesign (DashboardV2).

## Language

**DashboardV2**:
The redesign project. All new components live in `src/components/dashboard-v2/`. Built alongside the old UI — pages are cut over atomically.
_Avoid_: Redesign, v2

**Calm Educational Intelligence**:
Core design philosophy. The platform should feel like a modern learning workspace where insights matter more than raw statistics. Inspired by Linear, Notion, Stripe Dashboard, and Khan Academy.
_Avoid_: Admin panel, SaaS template, generic dashboard

**InsightCard**:
Replacement for StatCard. Shows title, primary value, trend indicator, and context. Single-purpose card for a learning-centric metric.
_Avoid_: StatCard, metric card, data card

**MetricStrip**:
Single horizontal surface showing multiple summary metrics. One container, not multiple cards.
_Avoid_: Metric grid, stat row

**SidebarV2**:
Collapsible sidebar (256px expanded, 72px collapsed) with smooth Framer Motion animation, active route indicator, search navigation, and keyboard shortcuts.
_Avoid_: Old sidebar, nav sidebar

**HeroSection**:
Mandatory section at the top of every dashboard page. Role-specific greeting or command-center summary. Receives data via props from the parent page.
_Avoid_: Page title, dashboard title

**ActivityTimeline**:
Vertical timeline of activity events. Replaces most activity tables. Shows user, action, and timestamp in a narrative format.
_Avoid_: Activity table, event list

**AIInsightPanel**:
Panel displaying AI-generated educational recommendations. Shown as actionable insight text, not raw data.
_Avoid_: AI recommendation list

**LearningProgress**:
Visual progress component with milestones, completion percentage, and learning path position.
_Avoid_: Progress bar, course progress

**ContextHeader**:
Breadcrumb-style sub-navigation showing current section within the dashboard hierarchy. Lives between SidebarV2 and the main content canvas.
_Avoid_: Breadcrumb, subnav

**DashboardLayout**:
Layout wrapper composing SidebarV2 + ContextHeader + main content canvas. Each v2 page wraps its content in this layout.
_Avoid_: Page layout, shell

**Design Tokens**:
Single source of truth at `src/styles/design-system.ts`. Exports colors, typography, spacing, shadows, radii, and motion values.
_Avoid_: Theme tokens, CSS variables

**StudentDashboard**:
v2 student dashboard at `src/components/dashboard-v2/dashboards/StudentDashboard.tsx`. Fetches from `/api/student/dashboard`. Shows hero, continue learning card, metric strip, weekly progress, topic mastery, weak topics, achievements, activity timeline, and AI insights.

**TeacherDashboard**:
v2 teacher dashboard at `src/components/dashboard-v2/dashboards/TeacherDashboard.tsx`. Fetches from `/api/teacher/dashboard` (or `/api/admin/dashboard` for admin role). Shows hero, metric strip, class health insight cards, recent activity logs, and AI insights.

**ParentDashboard**:
v2 parent dashboard at `src/components/dashboard-v2/dashboards/ParentDashboard.tsx`. Fetches children from `/api/parent/children`, then per-child progress and weekly summary. Shows hero, child selector, metric strip, topic mastery bars, quiz results, weekly summary, and AI insights.

**SchoolDashboard**:
v2 school dashboard at `src/components/dashboard-v2/dashboards/SchoolDashboard.tsx`. Fetches schools from `/teacher/schools`, then profile + trends per school. Shows hero, school selector, metric strip, health distribution, health trend bars, at-risk classrooms, teacher activity, and AI insights.

**AdminDashboard**:
v2 admin dashboard at `src/components/dashboard-v2/dashboards/AdminDashboard.tsx`. Fetches from `/api/admin/dashboard`. Shows hero, metric strip, platform insight cards, recent users, system activity logs, and AI insights.

**V2OverviewPage**:
Role dispatcher at `/v2/overview/page.tsx`. Checks `getUserRole()` and renders the matching dashboard: Student, Teacher, Parent, School, or Admin.

## i18n

next-intl 4, locales `en` + `am`, catalogs in `messages/{en,am}.json` (full parity, CI-enforced).

- **Single middleware**: `src/middleware.ts` (auth) only. Never add a root `middleware.ts` — Next.js silently registers just one, and the root one won (breaks auth) or loses (breaks i18n) depending on version.
- **Locale resolution**: `i18n.ts` reads the `NEXT_LOCALE` cookie, validates against `LOCALES`, deep-merges the active locale **over English** (`src/lib/i18n-merge.ts`) so untranslated keys render English, never raw dotted keys. Root layout consumes it via `getLocale()`/`getMessages()`; do not hand-load message JSON elsewhere. Isomorphic constants (`LOCALES`, `LOCALE_COOKIE`, `isLocale`) live in `src/lib/i18n-config.ts` — import those from client code, never the server-only `i18n.ts`.
- **Language switching**: always via `src/components/LanguageSwitcher.tsx` (`variant="select" | "toggle"`) backed by `src/hooks/useLocaleSwitcher.ts` — one cookie write + backend preference sync + `router.refresh()`. Do not hand-roll cookie writes.
- **Guardrail**: `npm run i18n:check` (CI: `dashboard-i18n` job, **strict**) fails on duplicate JSON keys, code-referenced keys missing from `en.json`, non-en keys unknown to `en.json`, **and any en→am parity gap**. New EN keys must ship with their AM translation in the same PR.
- **Adding UI text**: add keys to both catalogs, use `useTranslations('namespace')` + `t('key')`; never concatenate message fragments or select plural twin-keys in code — use ICU (`{count, plural, one {...} other {...}}`); never bake colons into labels. All app pages are translated: DashboardV2 core (`v2.*`), workspace (`workspace.*`), assignments (`assignments.*`), assessment-studio (`studio.*`), knowledge-graph (`graph.*`), digital-twin (`twin.*`), intervention-analytics (`analytics.*`), admin pages (`admin.*`). Still English-only: shared components `components/{agents,governance,misconceptions}` (AgentCard, ExecutionPanel, ReflectionTable, ReviewQueue, ReviewDetail, MisconceptionPanel), API-driven content (quiz/lesson text, topics, AI summaries), and e2e-only strings. Also open: pass locale to backend APIs for Amharic LLM content; native-speaker review of `messages/am.json`.
- **Amharic rendering**: body/display/heading font stacks include Ethiopic fallbacks (`Noto Sans Ethiopic`, `Ebrima`, `Abyssinica SIL`); `html[lang='am']` gets increased line-height.
