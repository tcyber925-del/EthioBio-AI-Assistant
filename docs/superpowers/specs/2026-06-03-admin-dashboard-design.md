# Admin Dashboard Design

## Overview

Build a standalone admin section in the dashboard for school/district administrators to manage users, content, schools, and monitor system health. Adds auth protection to existing backend admin endpoints and builds 5 frontend pages.

## Backend Changes

### Auth for existing admin endpoints

All `GET /admin/dashboard`, `GET /admin/content/review`, `GET /admin/monitoring`, `GET /admin/content/quiz/{id}`, `GET /admin/content/lesson/{id}`, and `PATCH /admin/content/{type}/{id}/status` currently have NO auth. Add:

```python
from src.api.auth import get_current_user
from src.database.models import User, UserRole
from fastapi import Depends, HTTPException

async def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required")
```

Inject as a dependency into every existing admin endpoint.

### New user management endpoints

Add to `src/api/admin.py`:

- `GET /admin/users` — List/search users with pagination. Query params: `search` (optional, matches email/telegram_id), `role` (optional filter), `page` (default 1), `per_page` (default 20). Returns `{ users: [...], total, page, per_page }`.
- `PATCH /admin/users/{user_id}/status` — Toggle user `is_active`. Body: `{ "is_active": bool }`.

### New school management for admins

The existing `/teacher/schools/*` and `/teacher/district/*` endpoints are already admin-protected via `_require_admin`. The admin frontend will call these directly through the proxy rewrite.

However, the existing `GET /teacher/schools` only returns `{ id, name, created_at }`. The admin dashboard needs richer data (teacher count, student count, grade range). Add `GET /admin/schools` that returns enriched school data computed from class_groups relationships — reuses `SchoolService` internally.

Also need `POST /teacher/schools` for school creation (currently missing — add to `src/api/teacher.py`).

## Frontend Architecture

### Route structure

```
/admin                  → AdminLayout → DashboardOverview
/admin/content          → ContentReview
/admin/content/quiz/[id] → QuizDetail
/admin/content/lesson/[id] → LessonDetail
/admin/monitoring       → Monitoring
/admin/schools          → Schools
/admin/users            → Users
```

### Layout

Create `dashboard/src/app/admin/layout.tsx` — standalone layout with:
- Admin sidebar (5 nav items + "Back to Dashboard" link)
- Top banner/header showing "Admin Panel" label
- Auth guard that checks JWT + admin role, redirects to `/login` if not authenticated, shows "Access denied" if role is not admin

### Auth guard flow

1. Check `localStorage` for JWT token
2. If no token → redirect to `/login`
3. If token exists → call `GET /admin/dashboard` to verify access (returns 403 if not admin)
4. On 403 → show "Access denied — admin privileges required" with "Back to Dashboard" button
5. On other error → show retry button (same pattern as UX-2 through UX-7)

### Pages

#### DashboardOverview (`/admin`)
- 5 KPI cards: Users, Teachers, Students, Quizzes, Lessons
- Recent Users table (20 most recent)
- Recent Model Logs table (20 most recent)
- Data from `GET /admin/dashboard`

#### ContentReview (`/admin/content`)
- Filters: Type (quiz/lesson/all), Status (draft/published/archived/all), Grade (all/9-12)
- Search input (filters by title client-side after fetching)
- Table with columns: Title, Type (badge), Grade, Status (badge), Created, Actions (View / Publish-or-Archive)
- Publish/Archive calls `PATCH /admin/content/{type}/{id}/status`
- Data from `GET /admin/content/review`

#### QuizDetail (`/admin/content/quiz/[id]`)
- Full quiz details: title, grade, topic, status, model used, created date
- Questions list: text, type, options, correct answer, explanation, difficulty
- Status toggle button (publish/archive)
- Data from `GET /admin/content/quiz/{id}`

#### LessonDetail (`/admin/content/lesson/[id]`)
- Full lesson details: topic, grade, objective, prior knowledge, explanation, activities, assessment, homework, teacher notes, status, model, created date
- Status toggle button
- Data from `GET /admin/content/lesson/{id}`

#### Monitoring (`/admin/monitoring`)
- 3 KPI cards: Total Requests, Failed, Fallback rate
- Data from `GET /admin/monitoring`

#### Schools (`/admin/schools`)
- School list with name, teacher count, student count, grade range
- "Add School" button that opens a form modal
- Data from `GET /admin/schools` — enriched with teacher_count, student_count, grade_range
- Add school calls `POST /teacher/schools` (creates a School record)
- School detail/overview via existing `GET /teacher/schools/{id}/overview`

#### Users (`/admin/users`)
- Search input (filters by email or telegram_id)
- Role filter chips: All, Student, Teacher, Parent, Admin
- User table: email, role badge, grade level, telegram_id, active/inactive badge, created date
- Toggle active/inactive button per row
- Data from `GET /admin/users`
- Toggle calls `PATCH /admin/users/{id}/status`

### Data fetching

Use the existing `fetchWithAuth` from `dashboard/src/lib/fetchWithAuth.ts`. All admin pages use the same pattern:

```tsx
const [data, setData] = useState<... | null>(null)
const [error, setError] = useState<string | null>(null)

useEffect(() => {
  fetchWithAuth('/admin/dashboard')
    .then(res => res.json())
    .then(setData)
    .catch(err => setError(err.message))
}, [])
```

## Testing

- Backend: Test admin auth (403 without token, 403 with non-admin token, 200 with admin token) for each endpoint
- Backend: Test user management endpoints (list, search, filter by role, toggle status)
- Frontend: No new tests (follows existing pattern of no frontend test suite)

## Files to modify

### Backend
- `src/api/admin.py` — Add auth deps to all endpoints, add `GET /admin/users`, `PATCH /admin/users/{id}/status`, `GET /admin/schools` (enriched)
- `src/api/teacher.py` — Add `POST /teacher/schools` for school creation (currently missing)

### Frontend
- `dashboard/src/app/admin/layout.tsx` — NEW: standalone admin layout with auth guard
- `dashboard/src/app/admin/page.tsx` — NEW: DashboardOverview
- `dashboard/src/app/admin/content/page.tsx` — NEW: ContentReview
- `dashboard/src/app/admin/content/quiz/[id]/page.tsx` — NEW: QuizDetail
- `dashboard/src/app/admin/content/lesson/[id]/page.tsx` — NEW: LessonDetail
- `dashboard/src/app/admin/monitoring/page.tsx` — NEW: Monitoring
- `dashboard/src/app/admin/schools/page.tsx` — NEW: Schools
- `dashboard/src/app/admin/users/page.tsx` — NEW: Users

## Out of scope
- School creation in the teacher API (`POST /teacher/schools`) is a prerequisite but tiny — included as a single backend change
- No CSV export, no bulk operations, no advanced analytics
- No changes to existing admin API response shapes
