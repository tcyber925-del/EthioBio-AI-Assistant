# Dashboard i18n — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add full Amharic localization to the Next.js dashboard using `next-intl`.

**Architecture:** Install `next-intl`, create JSON translation catalogs (`messages/en.json`, `messages/am.json`), add middleware for locale cookie handling, wrap layouts with `NextIntlClientProvider`, replace all hardcoded English strings with `useTranslations()` calls (~170 keys across 46 files).

**Tech Stack:** Next.js 14, next-intl, React, TypeScript, Tailwind CSS

---

### Task 1: Install next-intl and create config files

**Files:**
- Modify: `dashboard/package.json`
- Modify: `dashboard/next.config.js`
- Create: `dashboard/i18n.ts`
- Create: `dashboard/middleware.ts`
- Create: `dashboard/messages/en.json`
- Create: `dashboard/messages/am.json`

- [ ] **Step 1: Install next-intl**

Run: `cd dashboard && npm install next-intl`

- [ ] **Step 2: Create i18n.ts config**

Create `dashboard/i18n.ts`:

```typescript
import { getRequestConfig } from 'next-intl/server';

export default getRequestConfig(async ({ locale }) => ({
  messages: (await import(`./messages/${locale}.json`)).default,
}));
```

- [ ] **Step 3: Create middleware.ts**

Create `dashboard/middleware.ts`:

```typescript
import createMiddleware from 'next-intl/middleware';

export default createMiddleware({
  locales: ['en', 'am'],
  defaultLocale: 'en',
  localeDetection: false,
  localePrefix: 'never',
});

export const config = {
  matcher: ['/((?!api|_next|_vercel|.*\\..*).*)'],
};
```

`localePrefix: 'never'` means no URL path prefix — locale read from cookie `NEXT_LOCALE`.

- [ ] **Step 4: Update next.config.js**

Read `dashboard/next.config.js` first. Replace content with:

```javascript
const createNextIntlPlugin = require('next-intl/plugin');

const withNextIntl = createNextIntlPlugin('./i18n.ts');

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    const api = process.env.NEXT_PUBLIC_API_URL || 'http://app:8000';
    return [
      { source: '/api/:path*', destination: `${api}/:path*` },
      { source: '/models/:path*', destination: `${api}/models/:path*` },
      { source: '/quiz/:path*', destination: `${api}/quiz/:path*` },
      { source: '/lesson-plan/:path*', destination: `${api}/lesson-plan/:path*` },
      { source: '/chat', destination: `${api}/chat` },
      { source: '/graph/:path*', destination: `${api}/graph/:path*` },
      { source: '/progress/:path*', destination: `${api}/progress/:path*` },
      { source: '/gamification/:path*', destination: `${api}/gamification/:path*` },
      { source: '/activity/:path*', destination: `${api}/activity/:path*` },
      { source: '/diagram/:path*', destination: `${api}/diagram/:path*` },
      { source: '/intelligence/:path*', destination: `${api}/intelligence/:path*` },
      { source: '/auth/:path*', destination: `${api}/auth/:path*` },
      { source: '/teacher/:path*', destination: `${api}/teacher/:path*` },
      { source: '/recovery/:path*', destination: `${api}/recovery/:path*` },
      { source: '/parent/:path*', destination: `${api}/parent/:path*` },
      { source: '/admin/:path*', destination: `${api}/admin/:path*` },
      { source: '/users/:path*', destination: `${api}/users/:path*` },
    ];
  },
};

module.exports = withNextIntl(nextConfig);
```

- [ ] **Step 5: Create stub message files**

Create `dashboard/messages/en.json`:
```json
{
  "sidebar": {
    "dashboard": "Dashboard",
    "classroom": "Classroom",
    "school": "School",
    "parent": "Parent",
    "recovery": "Recovery",
    "quizzes": "Quizzes",
    "lessons": "Lesson Plans",
    "students": "Students",
    "monitoring": "Monitoring",
    "diagrams": "Diagrams",
    "ask": "Ask Q&A",
    "admin_panel": "Admin Panel",
    "parent_dashboard": "Parent Dashboard",
    "teacher_dashboard": "Teacher Dashboard",
    "student_dashboard": "Student Dashboard",
    "sign_out": "Sign Out",
    "grade_curriculum": "Grade 9-12 curriculum",
    "language": "Language",
    "english": "English",
    "amharic": "Amharic"
  },
  "login": {
    "title": "EthioSci AI Assistant",
    "subtitle": "Personalized Biology Tutoring for Ethiopian Grades 7-12",
    "email": "Email",
    "password": "Password",
    "sign_in": "Sign In",
    "create_account": "Create Account",
    "create_and_sign_in": "Create & Sign In",
    "please_wait": "Please wait...",
    "register_as": "Register as",
    "teacher": "Teacher",
    "student": "Student",
    "parent": "Parent",
    "already_have_account": "Already have an account?",
    "new_teacher": "New teacher?",
    "telegram_otp": "Telegram OTP Login",
    "telegram_id": "Telegram ID",
    "telegram_id_hint": "Your numeric Telegram ID",
    "otp_code": "6-digit code",
    "send_otp": "Send OTP",
    "sending": "Sending...",
    "verify_login": "Verify & Login",
    "verifying": "Verifying...",
    "login_telegram": "Login with Telegram",
    "back_to_email": "Back to email login",
    "error_invalid_credentials": "Invalid email or password",
    "error_email_exists": "Email already registered"
  },
  "common": {
    "loading": "Loading...",
    "error": "Something went wrong",
    "retry": "Retry",
    "save": "Save",
    "cancel": "Cancel",
    "back": "Back",
    "refresh": "Refresh",
    "search": "Search",
    "filter": "Filter",
    "previous": "Previous",
    "next": "Next",
    "no_data": "No data available",
    "empty": "No items found",
    "confirm": "Confirm",
    "yes": "Yes",
    "no": "No",
    "actions": "Actions",
    "status": "Status",
    "created": "Created",
    "type": "Type"
  },
  "admin": {
    "dashboard": {
      "title": "Admin Dashboard",
      "total_users": "Total Users",
      "total_teachers": "Teachers",
      "total_students": "Students",
      "total_parents": "Parents",
      "active_sessions": "Active Sessions",
      "recent_activity": "Recent Activity",
      "system_health": "System Health"
    },
    "users": {
      "title": "User Management",
      "search_placeholder": "Search by name or email...",
      "role_all": "All Roles",
      "role_admin": "Admin",
      "role_teacher": "Teacher",
      "role_student": "Student",
      "role_parent": "Parent",
      "email": "Email",
      "role": "Role",
      "telegram": "Telegram",
      "children": "Children",
      "status_active": "Active",
      "status_inactive": "Inactive",
      "deactivate": "Deactivate",
      "activate": "Activate",
      "change_role": "Change Role",
      "no_users": "No users found"
    },
    "schools": {
      "title": "Schools",
      "add_school": "Add School",
      "name": "School Name",
      "code": "Code",
      "teacher_count": "Teachers",
      "student_count": "Students"
    },
    "monitoring": {
      "title": "Monitoring",
      "latency": "Latency",
      "requests": "Requests",
      "errors": "Errors",
      "model_performance": "Model Performance"
    },
    "content": {
      "title": "Content Review",
      "quiz": "Quiz Review",
      "lesson": "Lesson Review",
      "approve": "Approve",
      "reject": "Reject",
      "published": "Published",
      "draft": "Draft"
    }
  },
  "student": {
    "dashboard": {
      "title": "Student Dashboard",
      "total_xp": "Total XP",
      "study_streak": "Study Streak",
      "mastery_progress": "Mastery Progress",
      "weak_topics": "Weak Topics",
      "due_reviews": "Due for Review",
      "recent_activity": "Recent Activity",
      "no_weak_topics": "No weak topics found — great job!",
      "no_reviews_due": "No reviews due",
      "no_activity": "No recent activity",
      "readiness": "Exam Readiness"
    },
    "mastery": {
      "title": "Topic Mastery",
      "score": "Score",
      "attempts": "Attempts",
      "no_data": "No mastery data yet"
    }
  },
  "parent": {
    "dashboard": {
      "title": "Parent Dashboard",
      "select_child": "Select a child to view progress",
      "weekly_summary": "Weekly Summary",
      "performance_warning": "Performance Warning",
      "no_children": "No children linked to your account",
      "amharic_summary": "አማርኛ"
    }
  },
  "teacher": {
    "dashboard": {
      "title": "Teacher Dashboard",
      "total_students": "Students",
      "active_quizzes": "Active Quizzes",
      "avg_readiness": "Avg Readiness",
      "intervention_rate": "Intervention Rate",
      "recent_activity": "Recent Activity",
      "classrooms": "My Classrooms",
      "no_classrooms": "No classrooms yet",
      "no_activity": "No recent activity"
    }
  },
  "classroom": {
    "title": "My Classrooms",
    "create": "Create Classroom",
    "students": "Students",
    "no_classrooms": "No classrooms yet",
    "back": "Back to Classrooms",
    "student_name": "Name",
    "student_grade": "Grade",
    "student_readiness": "Readiness",
    "no_students": "No students in this classroom"
  },
  "quiz": {
    "title": "Quizzes",
    "generate": "Generate Quiz",
    "topic": "Topic",
    "grade": "Grade",
    "questions": "Questions",
    "score": "Score",
    "no_quizzes": "No quizzes found",
    "back": "Back to Quizzes",
    "generate_title": "Generate Quiz",
    "select_topic": "Select topic",
    "question_count": "Number of questions",
    "generating": "Generating..."
  },
  "lesson": {
    "title": "Lesson Plans",
    "create": "Create Lesson Plan",
    "topic": "Topic",
    "grade": "Grade",
    "duration": "Duration",
    "no_lessons": "No lesson plans found",
    "back": "Back to Lessons",
    "create_title": "Create Lesson Plan",
    "select_topic": "Select topic",
    "generating": "Creating..."
  },
  "monitoring": {
    "title": "Monitoring",
    "overview": "Overview",
    "recent_queries": "Recent Queries",
    "error_logs": "Error Logs",
    "no_data": "No monitoring data yet",
    "no_queries": "No recent queries",
    "no_errors": "No errors"
  },
  "diagrams": {
    "title": "Biology Diagrams",
    "generate": "Generate Diagram",
    "description": "Generate biology diagrams by describing what you need",
    "generating": "Generating...",
    "no_diagrams": "Generate a diagram to get started"
  },
  "ask": {
    "title": "Ask Q&A",
    "placeholder": "Ask a biology question...",
    "ask_button": "Ask",
    "thinking": "Thinking...",
    "no_questions": "Ask a question to get started"
  },
  "recovery": {
    "title": "Recovery Dashboard",
    "weak_topics": "Weak Topics",
    "active_plans": "Active Plans",
    "completion": "Completion",
    "tasks_completed": "Tasks completed",
    "no_weak_topics": "No weak topics identified",
    "no_plans": "No active recovery plans",
    "radar_chart": "Topic Radar",
    "progress_trend": "Progress Trend",
    "heatmap": "Activity Heatmap",
    "learning_tree": "Learning Tree"
  },
  "gamification": {
    "total_xp": "Total XP",
    "level": "Level",
    "xp_to_next": "XP to next level",
    "xp_earned": "XP earned",
    "study_streak": "Study Streak",
    "current": "Current",
    "longest": "Longest",
    "mastery_progress": "Mastery Progress",
    "recovery_progress": "Recovery Progress",
    "achievements": "Achievements",
    "unlocked": "Unlocked",
    "locked": "Locked",
    "achievement_first_steps": "First Steps",
    "achievement_first_steps_desc": "Complete your first quiz",
    "achievement_quiz_master": "Quiz Master",
    "achievement_quiz_master_desc": "Complete 10 quizzes",
    "achievement_perfect_score": "Perfect Score",
    "achievement_perfect_score_desc": "Get 100% on any quiz",
    "achievement_streak_starter": "Streak Starter",
    "achievement_streak_starter_desc": "3-day study streak",
    "achievement_dedicated": "Dedicated",
    "achievement_dedicated_desc": "7-day study streak",
    "achievement_scholar": "Scholar",
    "achievement_scholar_desc": "30-day study streak",
    "achievement_xp_hunter": "XP Hunter",
    "achievement_xp_hunter_desc": "Earn 1000 total XP",
    "achievement_biology_expert": "Biology Expert",
    "achievement_biology_expert_desc": "Reach Level 5",
    "achievement_master_biologist": "Master Biologist",
    "achievement_master_biologist_desc": "Reach Level 10"
  }
}
```

- [ ] **Step 6: Create Amharic message file**

Copy `dashboard/messages/en.json` to `dashboard/messages/am.json`. Replace every English value with its Amharic translation. Use these translations (exact content for keys):

```json
{
  "sidebar": {
    "dashboard": "ዳሽቦርድ",
    "classroom": "ክፍል",
    "school": "ትምህርት ቤት",
    "parent": "ወላጅ",
    "recovery": "ማገገሚያ",
    "quizzes": "ፈተናዎች",
    "lessons": "የትምህርት እቅዶች",
    "students": "ተማሪዎች",
    "monitoring": "ክትትል",
    "diagrams": "ሥዕላዊ መግለጫዎች",
    "ask": "ጥያቄ ጠይቅ",
    "admin_panel": "የአስተዳዳሪ ፓነል",
    "parent_dashboard": "የወላጅ ዳሽቦርድ",
    "teacher_dashboard": "የመምህር ዳሽቦርድ",
    "student_dashboard": "የተማሪ ዳሽቦርድ",
    "sign_out": "ውጣ",
    "grade_curriculum": "ከ9-12 ክፍል ሥርዓተ ትምህርት",
    "language": "ቋንቋ",
    "english": "እንግሊዝኛ",
    "amharic": "አማርኛ"
  },
  "login": {
    "title": "EthioSci AI ረዳት",
    "subtitle": "ለኢትዮጵያ 7-12 ክፍሎች የተበጀ የባዮሎጂ ትምህርት",
    "email": "ኢሜይል",
    "password": "የይለፍ ቃል",
    "sign_in": "ግባ",
    "create_account": "መለያ ፍጠር",
    "create_and_sign_in": "ፍጠር እና ግባ",
    "please_wait": "እባክዎ ይጠብቁ...",
    "register_as": "ሆነው ይመዝገቡ",
    "teacher": "መምህር",
    "student": "ተማሪ",
    "parent": "ወላጅ",
    "already_have_account": "መለያ አለዎት?",
    "new_teacher": "አዲስ መምህር?",
    "telegram_otp": "በቴሌግራም OTP ይግቡ",
    "telegram_id": "የቴሌግራም መለያ",
    "telegram_id_hint": "የእርስዎ የቴሌግራም ቁጥር",
    "otp_code": የ6 አሃዝ ኮድ",
    "send_otp": "OTP ላክ",
    "sending": "በመላክ ላይ...",
    "verify_login": "አረጋግጥ እና ግባ",
    "verifying": "በማረጋገጥ ላይ...",
    "login_telegram": "በቴሌግራም ግባ",
    "back_to_email": "ወደ ኢሜይል መግቢያ ተመለስ",
    "error_invalid_credentials": "ልክ ያልሆነ ኢሜይል ወይም የይለፍ ቃል",
    "error_email_exists": "ኢሜይል ቀድሞ ተመዝግቧል"
  },
  "common": {
    "loading": "በመጫን ላይ...",
    "error": "የሆነ ስህተት ተፈጥሯል",
    "retry": "ደግሞ ሞክር",
    "save": "አስቀምጥ",
    "cancel": "ሰርዝ",
    "back": "ተመለስ",
    "refresh": "አድስ",
    "search": "ፈልግ",
    "filter": "አጣራ",
    "previous": "ቀዳሚ",
    "next": "ቀጣይ",
    "no_data": "ምንም መረጃ የለም",
    "empty": "ምንም ዕቃዎች አልተገኙም",
    "confirm": "አረጋግጥ",
    "yes": "አዎ",
    "no": "አይ",
    "actions": "ተግባራት",
    "status": "ሁኔታ",
    "created": "የተፈጠረ",
    "type": "አይነት"
  },
  "admin": {
    "dashboard": { ... },
    "users": { ... },
    "schools": { ... },
    "monitoring": { ... },
    "content": { ... }
  },
  "student": { ... },
  "parent": { ... },
  "teacher": { ... },
  "classroom": { ... },
  "quiz": { ... },
  "lesson": { ... },
  "monitoring": { ... },
  "diagrams": { ... },
  "ask": { ... },
  "recovery": { ... },
  "gamification": { ... }
}
```

For the full `am.json`, translate each English value to Amharic. The JSON keys stay identical. This is a large but mechanical translation job.

- [ ] **Step 7: Commit**

```bash
git add dashboard/package.json dashboard/next.config.js dashboard/i18n.ts dashboard/middleware.ts dashboard/messages/
git commit -m "feat(i18n): install next-intl, add config and translation files"
```

---

### Task 2: Update layouts with NextIntlClientProvider

**Files:**
- Modify: `dashboard/src/app/layout.tsx`
- Modify: `dashboard/src/app/admin/layout.tsx`

- [ ] **Step 1: Update root layout.tsx**

Read `dashboard/src/app/layout.tsx`. Replace with:

```tsx
import type { Metadata } from 'next';
import { NextIntlClientProvider } from 'next-intl';
import { getMessages } from 'next-intl/server';
import Sidebar from '@/components/Sidebar';
import './globals.css';

export const metadata: Metadata = {
  title: 'EthioSci AI Assistant',
  description: 'Personalized Biology Tutoring for Ethiopian Grades 7-12',
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const messages = await getMessages();

  return (
    <html lang="en">
      <body className="bg-background text-foreground font-sans">
        <NextIntlClientProvider messages={messages}>
          <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <main className="flex-1 p-6 lg:p-8 overflow-auto">
              {children}
            </main>
          </div>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
```

Note: The `<html lang>` is set dynamically by `next-intl` middleware via the `NEXT_LOCALE` cookie. We can keep `lang="en"` as static attribute since middleware handles it at the request level. Actually, for the root layout, `next-intl` recommends using `unstable_setRequestLocale` or making the layout receive the locale. But since we use `localePrefix: 'never'`, the layout itself won't have a dynamic `params.locale`. Instead, we rely on `getMessages()` which reads locale from the cookie.

Actually, `getMessages()` needs the locale to be available. With `localePrefix: 'never'`, we need to pass locale manually. Let me use a different approach — use `getLocale()` from `next-intl/server`:

```tsx
import { getLocale, getMessages } from 'next-intl/server';

export default async function RootLayout({ children }) {
  const locale = await getLocale();
  const messages = await getMessages();
  
  return (
    <html lang={locale}>
      {/* ... */}
    </html>
  );
}
```

- [ ] **Step 2: Update admin layout.tsx**

Same pattern — read the file, add `NextIntlClientProvider` wrapper if it has its own layout (it does — it's a separate sidebar layout).

Read `dashboard/src/app/admin/layout.tsx` first, then add imports and wrapping:

```tsx
import { NextIntlClientProvider } from 'next-intl';
import { getMessages } from 'next-intl/server';

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const messages = await getMessages();
  
  return (
    <NextIntlClientProvider messages={messages}>
      {/* existing admin layout content */}
    </NextIntlClientProvider>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/app/layout.tsx dashboard/src/app/admin/layout.tsx
git commit -m "feat(i18n): wrap layouts with NextIntlClientProvider"
```

---

### Task 3: Migrate Sidebar.tsx and add language switcher

**Files:**
- Modify: `dashboard/src/components/Sidebar.tsx`

- [ ] **Step 1: Read current Sidebar.tsx**

Read `dashboard/src/components/Sidebar.tsx` to understand current structure.

- [ ] **Step 2: Rewrite with useTranslations + language switcher**

Replace all hardcoded strings with `t()` calls. Add language switcher dropdown in the footer.

```tsx
'use client';

import { useTranslations, useLocale } from 'next-intl';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { getUserRole, signOut } from '@/lib/auth';
import { setCookie } from '@/lib/cookies';
import {
  LayoutDashboard, Users, BookOpen, FileQuestion, BarChart3,
  GraduationCap, School, UserCheck, UserCog, Shield, HelpCircle,
  LogOut, ChevronDown, Activity, GitFork,
} from 'lucide-react';

// ... allLinks array (same but labels removed — they come from t())

export default function Sidebar() {
  const t = useTranslations('sidebar');
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();
  const role = getUserRole();

  const allLinks = [
    { href: '/admin', icon: Shield, label: t('admin_panel'), roles: ['admin'] },
    { href: '/', icon: LayoutDashboard, label: role === 'admin' ? t('dashboard') : role === 'parent' ? t('parent_dashboard') : t('teacher_dashboard'), roles: ['admin', 'teacher', 'parent'] },
    { href: '/student', icon: GraduationCap, label: t('student_dashboard'), roles: ['student'] },
    { href: '/classroom', icon: Users, label: t('classroom'), roles: ['admin', 'teacher'] },
    { href: '/school', icon: School, label: t('school'), roles: ['admin', 'teacher'] },
    { href: '/parent', icon: UserCheck, label: t('parent'), roles: ['admin', 'parent'] },
    { href: '/recovery', icon: Activity, label: t('recovery'), roles: ['admin', 'teacher', 'student'] },
    { href: '/quizzes', icon: FileQuestion, label: t('quizzes'), roles: ['admin', 'teacher'] },
    { href: '/lessons', icon: BookOpen, label: t('lessons'), roles: ['admin', 'teacher'] },
    { href: '/students', icon: GraduationCap, label: t('students'), roles: ['admin', 'teacher'] },
    { href: '/monitoring', icon: BarChart3, label: t('monitoring'), roles: ['admin', 'teacher'] },
    { href: '/diagrams', icon: GitFork, label: t('diagrams'), roles: ['admin', 'teacher', 'student'] },
    { href: '/ask', icon: HelpCircle, label: t('ask'), roles: ['admin', 'teacher', 'student'] },
  ];

  const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLocale = e.target.value;
    setCookie('NEXT_LOCALE', newLocale, 365);
    // Sync to backend
    const userId = getUserId();
    if (userId) {
      fetch(`/api/users/${userId}/language?language=${newLocale}`, { method: 'PATCH' }).catch(() => {});
    }
    router.refresh();
  };

  // ... rest of component with t('sign_out'), t('grade_curriculum'), t('english'), t('amharic'), t('language')
}
```

- [ ] **Step 3: Add cookie utility**

Create `dashboard/src/lib/cookies.ts`:

```typescript
export function setCookie(name: string, value: string, days: number = 365) {
  const date = new Date();
  date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000);
  document.cookie = `${name}=${value};path=/;expires=${date.toUTCString()};SameSite=Lax`;
}
```

- [ ] **Step 4: Add import for getUserId in Sidebar**

Need to import `getUserId` from `@/lib/auth`:

Add `getUserId` to the import from `@/lib/auth`:
```tsx
import { getUserRole, getUserId, signOut } from '@/lib/auth';
```

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/components/Sidebar.tsx dashboard/src/lib/cookies.ts
git commit -m "feat(i18n): migrate Sidebar strings, add language switcher"
```

---

### Task 4: Migrate page-level files (batch 1 — core pages)

**Files:**
- Modify: `dashboard/src/app/page.tsx`
- Modify: `dashboard/src/app/login/page.tsx`
- Modify: `dashboard/src/app/student/page.tsx`
- Modify: `dashboard/src/app/parent/page.tsx`
- Modify: `dashboard/src/app/recovery/page.tsx`

For each file:
1. Add `import { useTranslations } from 'next-intl';` and `'use client';` if not already
2. Add `const t = useTranslations('namespace');` at top of component
3. Replace every hardcoded English string literal with `t('key')` calls

**Pattern for page.tsx:**

```tsx
'use client';
import { useTranslations } from 'next-intl';

export default function SomePage() {
  const t = useTranslations('namespace');
  // ...
  return (
    <div>
      <h1>{t('title')}</h1>
      {/* ... */}
    </div>
  );
}
```

- [ ] **Step 1: Migrate page.tsx** — use namespace `teacher.dashboard` (or for admin: `admin.dashboard`)
- [ ] **Step 2: Migrate login/page.tsx** — use namespace `login`, fetch language on login
- [ ] **Step 3: Migrate student/page.tsx** — use namespace `student.dashboard`
- [ ] **Step 4: Migrate parent/page.tsx** — use namespace `parent`
- [ ] **Step 5: Migrate recovery/page.tsx** — use namespace `recovery`

On login success, after storing the JWT, also read the user data and set `NEXT_LOCALE` cookie:

```typescript
// After successful login response
if (userData.language_preference) {
  setCookie('NEXT_LOCALE', userData.language_preference, 365);
}
```

- [ ] **Step 6: Commit**

```bash
git add dashboard/src/app/page.tsx dashboard/src/app/login/page.tsx dashboard/src/app/student/page.tsx dashboard/src/app/parent/page.tsx dashboard/src/app/recovery/page.tsx
git commit -m "feat(i18n): migrate core page strings"
```

---

### Task 5: Migrate page-level files (batch 2 — content pages)

**Files:**
- Modify: `dashboard/src/app/classroom/page.tsx`
- Modify: `dashboard/src/app/classroom/[id]/page.tsx`
- Modify: `dashboard/src/app/quizzes/page.tsx`
- Modify: `dashboard/src/app/quizzes/[id]/page.tsx`
- Modify: `dashboard/src/app/lessons/page.tsx`
- Modify: `dashboard/src/app/lessons/[id]/page.tsx`

Same pattern as Task 4 — add `useTranslations`, replace all strings.

- [ ] **Step 1: Migrate classroom pages** — namespace `classroom`
- [ ] **Step 2: Migrate quiz pages** — namespace `quiz`
- [ ] **Step 3: Migrate lesson pages** — namespace `lesson`
- [ ] **Step 4: Commit**

```bash
git add dashboard/src/app/classroom/ dashboard/src/app/quizzes/ dashboard/src/app/lessons/
git commit -m "feat(i18n): migrate classroom, quiz, lesson page strings"
```

---

### Task 6: Migrate remaining pages

**Files:**
- Modify: `dashboard/src/app/students/page.tsx`
- Modify: `dashboard/src/app/students/[id]/page.tsx`
- Modify: `dashboard/src/app/school/page.tsx`
- Modify: `dashboard/src/app/monitoring/page.tsx`
- Modify: `dashboard/src/app/diagrams/page.tsx`
- Modify: `dashboard/src/app/ask/page.tsx`
- Modify: `dashboard/src/app/admin/page.tsx`
- Modify: `dashboard/src/app/admin/users/page.tsx`
- Modify: `dashboard/src/app/admin/schools/page.tsx`
- Modify: `dashboard/src/app/admin/monitoring/page.tsx`
- Modify: `dashboard/src/app/admin/content/page.tsx`
- Modify: `dashboard/src/app/admin/content/quiz/[id]/page.tsx`
- Modify: `dashboard/src/app/admin/content/lesson/[id]/page.tsx`

Same pattern — namespace per page group:
- `students` for students pages
- `admin.users` for admin/users
- `admin.schools` for admin/schools
- etc.

- [ ] **Step 1-4: Batch migrate** in 2-3 sub-steps
- [ ] **Step 5: Commit**

```bash
git add dashboard/src/app/students/ dashboard/src/app/school/ dashboard/src/app/monitoring/ dashboard/src/app/diagrams/ dashboard/src/app/ask/ dashboard/src/app/admin/
git commit -m "feat(i18n): migrate remaining page strings"
```

---

### Task 7: Migrate components

**Files:**
- Modify: `dashboard/src/components/StatCard.tsx`
- Modify: `dashboard/src/components/Skeleton.tsx`
- Modify: `dashboard/src/components/ModelSelector.tsx`
- Modify: `dashboard/src/components/MarkdownRenderer.tsx`
- Modify: `dashboard/src/components/ActivityFeed.tsx`
- Modify: `dashboard/src/components/gamification/GamificationProfile.tsx`
- Modify: `dashboard/src/components/gamification/XpCard.tsx`
- Modify: `dashboard/src/components/gamification/StreakWidget.tsx`
- Modify: `dashboard/src/components/gamification/MasteryProgressBar.tsx`
- Modify: `dashboard/src/components/gamification/AchievementPanel.tsx`
- Modify: `dashboard/src/components/gamification/RecoveryProgressCard.tsx`
- Modify: `dashboard/src/components/learning/ContinueLearningFeed.tsx`
- Modify: `dashboard/src/components/learning/ExamReadinessCard.tsx`
- Modify: `dashboard/src/components/recovery/MasteryRadarChart.tsx`
- Modify: `dashboard/src/components/recovery/TopicHeatmap.tsx`
- Modify: `dashboard/src/components/recovery/ProgressTrendGraph.tsx`
- Modify: `dashboard/src/components/recovery/LearningTree.tsx`

Namespace mapping:
- `common` for shared components (StatCard, Skeleton, ModelSelector)
- `gamification` for gamification components
- `recovery` for recovery components
- `common` for ActivityFeed, MarkdownRenderer, learning components

- [ ] **Step 1: Migrate shared components** (StatCard, Skeleton, ModelSelector, MarkdownRenderer, ActivityFeed)
- [ ] **Step 2: Migrate gamification components**
- [ ] **Step 3: Migrate recovery components**
- [ ] **Step 4: Migrate learning components**
- [ ] **Step 5: Commit**

```bash
git add dashboard/src/components/
git commit -m "feat(i18n): migrate all component strings"
```

---

### Task 8: Date formatting with locale

**Files:**
- All files that call `toLocaleDateString()` (~17 call sites)

- [ ] **Step 1: Find all toLocaleDateString calls**

Run: `rg 'toLocaleDateString' dashboard/src/ --include '*.tsx'`

- [ ] **Step 2: Update each call to pass locale**

For each file that has date formatting:
1. Add `import { useLocale } from 'next-intl';` and `const locale = useLocale();`
2. Change `date.toLocaleDateString()` → `date.toLocaleDateString(locale)`
3. Change `date.toLocaleDateString('en-US', {...})` → `date.toLocaleDateString(locale, {...})`

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat(i18n): pass locale to date formatting calls"
```

---

### Task 9: TypeScript typecheck

- [ ] **Step 1: Typecheck**

Run: `cd dashboard && npx tsc --noEmit`

Fix any type errors.

- [ ] **Step 2: Build test**

Run: `cd dashboard && npm run build` (or `next build`)

Expected: Build succeeds with no errors.

- [ ] **Step 3: Commit any fixes**

```bash
git add -A
git commit -m "chore(i18n): fix typecheck and build issues"
```
