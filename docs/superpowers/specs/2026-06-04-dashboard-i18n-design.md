# Dashboard i18n — next-intl Migration

## Overview

Add full Amharic localization to the Next.js dashboard using `next-intl`. ~170 hardcoded English strings across 46 source files migrated to JSON translation catalogs with a language switcher and backend sync.

## Design

### 1. Library & Setup

- Install `next-intl`
- Create `messages/en.json` and `messages/am.json` — same key structure, Amharic values
- Add `i18n` block in `next.config.js`
- Create `i18n.ts` routing config + `middleware.ts` (reads `NEXT_LOCALE` cookie, default `en`)
- Wrap layout with `NextIntlClientProvider`

### 2. Translation Key Namespaces

| Namespace | Scope | Approx Keys |
|-----------|-------|-------------|
| `sidebar` | Sidebar.tsx | 15 |
| `login` | login/page.tsx | 15 |
| `admin` | admin/* pages | 25 |
| `student` | student/page.tsx | 15 |
| `parent` | parent/page.tsx | 10 |
| `common` | shared labels (loading, error, back, save, cancel) | 20 |
| `gamification` | gamification components | 15 |
| `recovery` | recovery components | 10 |
| `classroom` | classroom pages | 15 |
| `quiz` | quiz pages | 10 |
| `lesson` | lesson pages | 10 |
| `monitoring` | monitoring pages | 10 |
| `diagrams` | diagrams page | 5 |
| **Total** | | **~170** |

### 3. Locale Persistence

- **On login**: Fetch `language_preference` from user data, set as cookie
- **On switch**: `<select>` in sidebar calls `setCookie("NEXT_LOCALE", lang)` + `PATCH /users/{id}/language` (reusing existing endpoint)
- **Middleware**: reads `NEXT_LOCALE` cookie → falls back to `en`

### 4. String Migration Pattern

```tsx
// Before
<h1>User Management</h1>
<button>Save Changes</button>
<p>No students found</p>

// After
import { useTranslations } from 'next-intl'
const t = useTranslations('admin.users')
// ...
<h1>{t('title')}</h1>
<button>{t('save')}</button>
<p>{t('empty')}</p>
```

Each file touched: add `useTranslations` import + call, replace all string literals with `t()` calls.

### 5. Language Switcher

Dropdown in `Sidebar.tsx` footer above "Sign Out":
- 🇬🇧 English → sets cookie to `en`, reloads
- 🇪🇹 አማርኛ → sets cookie to `am`, syncs to backend, reloads

### 6. Date Formatting

Find all `toLocaleDateString()` calls (~17 across all files), replace with `toLocaleDateString(locale)` using `useLocale()` from `next-intl`.

### 7. Files Changed

| File | Change |
|------|--------|
| `package.json` | Add `next-intl` |
| `next.config.js` | Add `createNextIntlPlugin` wrapper, `i18n` routing |
| `middleware.ts` | **New** — locale cookie routing |
| `i18n.ts` | **New** — `next-intl` config |
| `messages/en.json` | **New** — ~170 English strings |
| `messages/am.json` | **New** — ~170 Amharic strings |
| `src/app/layout.tsx` | Wrap with `NextIntlClientProvider`, dynamic `<html lang>` |
| `src/app/admin/layout.tsx` | Same wrapping |
| `src/app/page.tsx` | Migrate strings |
| `src/app/login/page.tsx` | Migrate strings + fetch language |
| `src/app/student/page.tsx` | Migrate strings |
| `src/app/parent/page.tsx` | Migrate strings |
| `src/app/school/page.tsx` | Migrate strings |
| `src/app/recovery/page.tsx` | Migrate strings |
| `src/app/monitoring/page.tsx` | Migrate strings |
| `src/app/diagrams/page.tsx` | Migrate strings |
| `src/app/ask/page.tsx` | Migrate strings |
| `src/app/classroom/page.tsx` | Migrate strings |
| `src/app/classroom/[id]/page.tsx` | Migrate strings |
| `src/app/quizzes/page.tsx` | Migrate strings |
| `src/app/quizzes/[id]/page.tsx` | Migrate strings |
| `src/app/lessons/page.tsx` | Migrate strings |
| `src/app/lessons/[id]/page.tsx` | Migrate strings |
| `src/app/students/page.tsx` | Migrate strings |
| `src/app/students/[id]/page.tsx` | Migrate strings |
| `src/app/admin/page.tsx` | Migrate strings |
| `src/app/admin/users/page.tsx` | Migrate strings |
| `src/app/admin/schools/page.tsx` | Migrate strings |
| `src/app/admin/monitoring/page.tsx` | Migrate strings |
| `src/app/admin/content/page.tsx` | Migrate strings |
| `src/components/Sidebar.tsx` | Migrate strings + language switcher |
| `src/components/StatCard.tsx` | Migrate strings |
| `src/components/ModelSelector.tsx` | Migrate strings |
| `src/components/MarkdownRenderer.tsx` | Migrate strings |
| `src/components/ActivityFeed.tsx` | Migrate strings |
| `src/components/Skeleton.tsx` | Migrate strings |
| All 5 gamification components | Migrate strings |
| All 4 recovery components | Migrate strings |
| Both learning components | Migrate strings |

### 8. Out of Scope

- RTL layout support (Amharic uses left-to-right)
- Server-side locale detection (cookie-based only)
- Auto-translating API data (quiz questions, AI responses, etc.)
