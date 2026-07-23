# Track 4 — Frontend Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move auth from localStorage to HTTP-only cookies, clean up dual-theme CSS, add component unit tests.

**Architecture:** Cookie-based auth (paired with backend Track 1). Remove legacy dark theme CSS variables. Vitest + React Testing Library for critical components.

**Tech Stack:** Next.js 14, TypeScript, Tailwind, Vitest, Testing Library

---

### Task 1: Client auth to HTTP-only cookies

**Files:**
- Modify: `dashboard/src/lib/auth.ts`
- Modify: `dashboard/src/lib/fetchWithAuth.ts`
- Modify: `dashboard/src/middleware.ts`

- [ ] **Step 1: Rewrite auth.ts to use cookies, not localStorage**

```typescript
// dashboard/src/lib/auth.ts
export function isAuthenticated(): boolean {
  // Check if access_token cookie exists — sent with credentials: 'include'
  // The backend sets HttpOnly cookies, so we can't read them from JS.
  // Instead, try a lightweight /auth/me call or check if we get 401 back.
  // For now, use a boolean flag set by the login flow.
  return document.cookie.includes("access_token=");
}

export function getToken(): string | null {
  // Cannot read HttpOnly cookie from JS
  // Tokens are managed server-side via cookies
  return null;
}

export function setToken(token: string): void {
  // No-op — tokens are set by backend via Set-Cookie
}

export function clearToken(): void {
  // Call /auth/logout instead
  fetch("/auth/logout", { method: "POST", credentials: "include" });
}

export function decodeToken(): { sub?: string; role?: string } | null {
  // Cannot decode HttpOnly cookie from JS
  // Use /auth/me endpoint instead
  return null;
}

export function getUserId(): string | null {
  return null;
}

export function getUserRole(): string {
  // Read from a non-sensitive cookie set alongside the HttpOnly one
  const match = document.cookie.match(/(?:^|;\s*)user_role=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}
```

- [ ] **Step 2: Update fetchWithAuth.ts**

```typescript
// dashboard/src/lib/fetchWithAuth.ts
export async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const res = await fetch(url, {
    ...options,
    credentials: "include",  // sends HttpOnly cookies
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (res.status === 401) {
    // Try refreshing the token
    const refreshRes = await fetch("/auth/refresh", {
      method: "POST",
      credentials: "include",
    });
    if (refreshRes.ok) {
      // Retry original request
      return fetch(url, {
        ...options,
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...options.headers,
        },
      });
    }
    // Refresh failed — redirect to login
    window.location.href = "/login";
    throw new Error("Session expired");
  }

  return res;
}
```

- [ ] **Step 3: Update middleware.ts for SSR cookie check**

```typescript
// dashboard/src/middleware.ts
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const hasAccess = request.cookies.has("access_token");
  const isLoginPage = request.nextUrl.pathname === "/login";
  const isPublic = request.nextUrl.pathname === "/";

  if (!hasAccess && !isLoginPage && !isPublic) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  const response = NextResponse.next();
  response.headers.set("x-pathname", request.nextUrl.pathname);
  return response;
}

export const config = {
  matcher: ["/((?!_next|static|favicon.ico).*)"],
};
```

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/lib/auth.ts dashboard/src/lib/fetchWithAuth.ts dashboard/src/middleware.ts
git commit -m "feat: migrate frontend auth from localStorage to HTTP-only cookies"
```

---

### Task 2: Theme cleanup — remove legacy dark theme

**Files:**
- Modify: `dashboard/src/app/globals.css`
- Remove: `dashboard/src/components/ui/StatCard.tsx` (if applicable)

- [ ] **Step 1: Remove legacy CSS variables from globals.css**

Remove these lines from `:root`:
```css
--background: #0a0e1a;
--foreground: #e2e8f0;
--card: #0f1420;
--card-foreground: #e2e8f0;
--primary: #10b981;
--primary-foreground: #0a0e1a;
/* and any other --legacy-* or non-v2-* variables */
```

Make `body` use v2 variables:
```css
body {
  background-color: var(--v2-bg, #fafafa);
  color: var(--v2-text-primary, #1a1a2e);
  font-family: var(--font-inter), system-ui, sans-serif;
}
```

- [ ] **Step 2: Remove StatCard.tsx if redundant**

Check if any file still imports `StatCard`. If not:
```bash
rm dashboard/src/components/ui/StatCard.tsx
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/app/globals.css
git rm dashboard/src/components/ui/StatCard.tsx  # if applicable
git commit -m "style: remove legacy dark theme, unify on v2 design tokens"
```

---

### Task 3: Add Vitest + component unit tests

**Files:**
- Create: `dashboard/vitest.config.ts`
- Modify: `dashboard/package.json`
- Create: `dashboard/src/components/dashboard-v2/__tests__/InsightCard.test.tsx`
- Create: `dashboard/src/components/dashboard-v2/__tests__/SidebarV2.test.tsx`

- [ ] **Step 1: Create vitest config**

```typescript
// dashboard/vitest.config.ts
import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    globals: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

- [ ] **Step 2: Create setup file**

```typescript
// dashboard/vitest.setup.ts
import "@testing-library/jest-dom";
```

- [ ] **Step 3: Add test script to package.json**

```json
"scripts": {
  "test": "vitest run",
  "test:watch": "vitest"
}
```

- [ ] **Step 4: Write InsightCard test**

```typescript
// dashboard/src/components/dashboard-v2/__tests__/InsightCard.test.tsx
import { render, screen } from "@testing-library/react";
import { InsightCard } from "../InsightCard";
import { describe, it, expect } from "vitest";

describe("InsightCard", () => {
  it("renders title and value", () => {
    render(<InsightCard title="Students" value="42" trend="up" />);
    expect(screen.getByText("Students")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders trend indicator", () => {
    render(<InsightCard title="Test" value="10" trend="down" />);
    expect(screen.getByText("↓")).toBeInTheDocument();
  });

  it("renders loading skeleton", () => {
    const { container } = render(<InsightCard title="Loading" loading />);
    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
  });
});
```

- [ ] **Step 5: Write SidebarV2 test**

```typescript
// dashboard/src/components/dashboard-v2/__tests__/SidebarV2.test.tsx
import { render, screen } from "@testing-library/react";
import { SidebarV2 } from "../SidebarV2";
import { describe, it, expect } from "vitest";

describe("SidebarV2", () => {
  it("renders navigation items for student role", () => {
    render(<SidebarV2 role="student" />);
    expect(screen.getByText("Overview")).toBeInTheDocument();
    expect(screen.getByText("Ask")).toBeInTheDocument();
  });

  it("collapses on toggle", () => {
    const { container } = render(<SidebarV2 role="teacher" />);
    const toggle = screen.getByLabelText("Toggle sidebar");
    toggle.click();
    expect(container.querySelector("w-16")).toBeInTheDocument();
  });
});
```

- [ ] **Step 6: Run tests**

```bash
cd dashboard && npx vitest run
```
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add dashboard/vitest.config.ts dashboard/vitest.setup.ts dashboard/package.json dashboard/src/components/dashboard-v2/__tests__/
git commit -m "test: add vitest with component unit tests for InsightCard and SidebarV2"
```
