# Admin Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build standalone admin dashboard with auth-protected backend endpoints and 5 frontend pages for system administration.

**Architecture:** Add `require_admin` dep to all existing admin endpoints, add user/school management endpoints. Frontend gets a standalone layout with admin sidebar, auth guard, and 5 pages using existing `fetchWithAuth` pattern.

**Tech Stack:** FastAPI, SQLAlchemy async, Next.js App Router, Tailwind CSS

---

### Task 1: Backend auth + user management + school endpoints

**Files:**
- Modify: `src/api/admin.py`
- Modify: `src/api/teacher.py`

- [ ] **Step 1: Add `require_admin` dependency and imports to admin.py**

```python
# src/api/admin.py — add at top alongside existing imports
from src.api.auth import get_current_user
from src.database.models import User, UserRole

async def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required")
```

- [ ] **Step 2: Add auth dep to all existing admin endpoints**

Replace each endpoint signature. Change:
```python
@router.get("/dashboard")
async def admin_dashboard(session: AsyncSession = Depends(get_session)):
```
To:
```python
@router.get("/dashboard")
async def admin_dashboard(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
```

Apply to all 6 existing endpoints: `GET /admin/dashboard`, `GET /admin/content/review`, `GET /admin/monitoring`, `GET /admin/content/quiz/{item_id}`, `GET /admin/content/lesson/{item_id}`, `PATCH /admin/content/{content_type}/{item_id}/status`.

- [ ] **Step 3: Add `GET /admin/users` endpoint**

```python
from sqlalchemy import func, or_

class UserListResponse(BaseModel):
    users: list[dict]
    total: int
    page: int
    per_page: int

@router.get("/users")
async def list_users(
    search: str | None = Query(None),
    role: str | None = Query(None, pattern="^(student|teacher|parent|admin)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    query = select(User)
    
    if search:
        query = query.where(
            or_(User.email.ilike(f"%{search}%"), User.telegram_id.cast(String).ilike(f"%{search}%"))
        )
    if role:
        query = query.where(User.role == UserRole[role])
    
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0
    
    query = query.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    users = result.scalars().all()
    
    return {
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "role": u.role.value if u.role else None,
                "grade_level": u.grade_level,
                "telegram_id": u.telegram_id,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }
```

- [ ] **Step 4: Add `PATCH /admin/users/{user_id}/status` endpoint**

```python
@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    body: dict,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    from uuid import UUID as UUIDType
    try:
        uid = UUIDType(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    is_active = body.get("is_active")
    if is_active is None:
        raise HTTPException(status_code=400, detail="is_active is required")
    
    user = await session.get(User, uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = bool(is_active)
    await session.commit()
    return {"ok": True, "user_id": user_id, "is_active": user.is_active}
```

- [ ] **Step 5: Add `GET /admin/schools` endpoint (enriched data)**

```python
@router.get("/schools")
async def list_admin_schools(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    result = await session.execute(
        select(School).options(selectinload(School.class_groups))
    )
    schools = result.scalars().all()
    
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "teacher_count": len({cg.teacher_id for cg in s.class_groups}),
            "student_count": sum(len(cg.students) for cg in s.class_groups),
            "grade_range": f"{min(cg.grade_level for cg in s.class_groups)}-{max(cg.grade_level for cg in s.class_groups)}"
            if s.class_groups else "N/A",
        }
        for s in schools
    ]
```

Note: Need to import `selectinload` at top of admin.py — add to existing imports.

- [ ] **Step 6: Add `POST /teacher/schools` endpoint to teacher.py**

```python
# In src/api/teacher.py — add a new endpoint for school creation
class CreateSchoolRequest(BaseModel):
    name: str

@router.post("/schools")
async def create_school(
    body: CreateSchoolRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    school = School(name=body.name)
    session.add(school)
    await session.commit()
    await session.refresh(school)
    return {
        "id": str(school.id),
        "name": school.name,
        "created_at": school.created_at.isoformat() if school.created_at else None,
    }
```

Add `CreateSchoolRequest` near the other Pydantic models at the top of `teacher.py`, and add `School` to the existing import if not already there.

---

### Task 2: Test admin API endpoints

**Files:**
- Create: `tests/test_admin_api.py`

- [ ] **Step 1: Write test for auth — rejects unauthenticated request**

```python
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database.session import get_session


@pytest.fixture
def mock_session():
    mock = AsyncMock()
    mock.scalar = AsyncMock(return_value=0)
    mock.execute = AsyncMock()
    mock.execute.return_value.scalars.return_value.all.return_value = []
    mock.get = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def client(mock_session):
    app.dependency_overrides[get_session] = lambda: mock_session
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_admin_dashboard_returns_401_without_token(client):
    resp = await client.get("/admin/dashboard")
    assert resp.status_code == 401
```

- [ ] **Step 2: Install httpx if needed**

Run: `./.venv/bin/pip install httpx` if not already installed. Check with `./.venv/bin/pip list | grep httpx`.

- [ ] **Step 3: Run test to verify it fails (or check current status)**

Run: `./.venv/bin/pytest tests/test_admin_api.py::test_admin_dashboard_returns_401_without_token -v`
Expected: PASS (endpoint not yet auth-guarded → returns 200, not 401; test will fail)

Actually this test may pass once auth is added. Let me adjust. Run it after Task 1.

- [ ] **Step 4: Write remaining admin tests**

```python
@pytest.mark.asyncio
async def test_admin_dashboard_returns_200_with_admin_token(client, mock_session):
    from src.api.auth import _create_access_token
    token = _create_access_token(str(uuid4()), "admin")
    resp = await client.get(
        "/admin/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_dashboard_returns_403_with_teacher_token(client, mock_session):
    from src.api.auth import _create_access_token
    token = _create_access_token(str(uuid4()), "teacher")
    resp = await client.get(
        "/admin/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_users_lists_users(client, mock_session):
    from src.api.auth import _create_access_token
    token = _create_access_token(str(uuid4()), "admin")
    resp = await client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "users" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_admin_users_status_toggle(client, mock_session):
    from src.api.auth import _create_access_token
    token = _create_access_token(str(uuid4()), "admin")
    user_id = str(uuid4())
    mock_user = AsyncMock()
    mock_user.is_active = True
    mock_session.get = AsyncMock(return_value=mock_user)
    
    resp = await client.patch(
        f"/admin/users/{user_id}/status",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_active"] is False
```

---

### Task 3: Admin layout with auth guard

**Files:**
- Create: `dashboard/src/app/admin/layout.tsx`

- [ ] **Step 1: Create admin layout component**

```tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

const NAV_ITEMS = [
  { href: '/admin', label: 'Dashboard', icon: '📊' },
  { href: '/admin/content', label: 'Content Review', icon: '📝' },
  { href: '/admin/schools', label: 'Schools', icon: '🏫' },
  { href: '/admin/users', label: 'Users', icon: '👥' },
  { href: '/admin/monitoring', label: 'Monitoring', icon: '📡' },
]

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const [authorized, setAuthorized] = useState<boolean | null>(null)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    if (!token) {
      router.push('/login')
      return
    }
    fetchWithAuth('/admin/dashboard')
      .then(res => {
        if (res.status === 403) {
          setError('Access denied — admin privileges required')
          return
        }
        if (!res.ok) throw new Error('Failed to verify admin access')
        setAuthorized(true)
      })
      .catch(err => {
        if (err.message?.includes('401')) {
          router.push('/login')
        } else {
          setError(err.message)
        }
      })
  }, [router])

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-bold text-red-600 mb-2">Access Denied</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <Link href="/" className="text-blue-600 hover:underline">
            Back to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  if (authorized === null) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">Verifying access...</p>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <aside className="w-56 bg-gray-900 text-white flex flex-col">
        <div className="p-4 border-b border-gray-700">
          <h1 className="text-lg font-bold">Admin Panel</h1>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {NAV_ITEMS.map(item => (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2 px-3 py-2 rounded text-sm ${
                pathname === item.href
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-800'
              }`}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>
        <div className="p-3 border-t border-gray-700">
          <Link href="/" className="flex items-center gap-2 text-sm text-gray-400 hover:text-white">
            <span>←</span>
            <span>Back to Dashboard</span>
          </Link>
        </div>
      </aside>
      <main className="flex-1 p-6">
        {children}
      </main>
    </div>
  )
}
```

---

### Task 4: Dashboard overview page

**Files:**
- Create: `dashboard/src/app/admin/page.tsx`

- [ ] **Step 1: Create dashboard overview page**

```tsx
'use client'

import { useEffect, useState } from 'react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

interface DashboardData {
  users: number
  teachers: number
  students: number
  quizzes: number
  lesson_plans: number
  quiz_attempts: number
  recent_users: Array<{ id: string; role: string; grade_level: number | null; created_at: string }>
  recent_logs: Array<{ id: string; request_type: string; model_used: string; success: boolean; latency_ms: number | null; created_at: string }>
}

export default function AdminDashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchWithAuth('/admin/dashboard')
      .then(res => res.json())
      .then(setData)
      .catch(err => setError(err.message))
  }, [])

  if (error) return <p className="text-red-600">Error: {error}</p>
  if (!data) return <p className="text-gray-500">Loading...</p>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard Overview</h1>
      <div className="grid grid-cols-5 gap-4 mb-8">
        {[
          { label: 'Users', value: data.users, color: 'bg-blue-50 text-blue-700' },
          { label: 'Teachers', value: data.teachers, color: 'bg-green-50 text-green-700' },
          { label: 'Students', value: data.students, color: 'bg-purple-50 text-purple-700' },
          { label: 'Quizzes', value: data.quizzes, color: 'bg-amber-50 text-amber-700' },
          { label: 'Lessons', value: data.lesson_plans, color: 'bg-rose-50 text-rose-700' },
        ].map(({ label, value, color }) => (
          <div key={label} className={`p-4 rounded-lg ${color}`}>
            <div className="text-2xl font-bold">{value}</div>
            <div className="text-sm">{label}</div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-6">
        <section>
          <h2 className="text-lg font-semibold mb-3">Recent Users</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-100">
                <th className="p-2 text-left">ID</th>
                <th className="p-2 text-left">Role</th>
                <th className="p-2 text-left">Grade</th>
                <th className="p-2 text-left">Created</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_users.map(u => (
                <tr key={u.id} className="border-t">
                  <td className="p-2 font-mono text-xs">{u.id.slice(0, 8)}...</td>
                  <td className="p-2 capitalize">{u.role}</td>
                  <td className="p-2">{u.grade_level ?? '-'}</td>
                  <td className="p-2 text-gray-500">{new Date(u.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        <section>
          <h2 className="text-lg font-semibold mb-3">Recent Model Logs</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-100">
                <th className="p-2 text-left">Type</th>
                <th className="p-2 text-left">Model</th>
                <th className="p-2 text-left">Status</th>
                <th className="p-2 text-left">Latency</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_logs.map(log => (
                <tr key={log.id} className="border-t">
                  <td className="p-2">{log.request_type}</td>
                  <td className="p-2 font-mono text-xs">{log.model_used}</td>
                  <td className="p-2">{log.success ? <span className="text-green-600">✓</span> : <span className="text-red-600">✗</span>}</td>
                  <td className="p-2">{log.latency_ms ? `${(log.latency_ms / 1000).toFixed(1)}s` : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </div>
  )
}
```

---

### Task 5: Content review + detail pages

**Files:**
- Create: `dashboard/src/app/admin/content/page.tsx`
- Create: `dashboard/src/app/admin/content/quiz/[id]/page.tsx`
- Create: `dashboard/src/app/admin/content/lesson/[id]/page.tsx`

- [ ] **Step 1: Create content review page**

`dashboard/src/app/admin/content/page.tsx`:
```tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

export default function AdminContentPage() {
  const [items, setItems] = useState<any[]>([])
  const [type, setType] = useState('all')
  const [status, setStatus] = useState('all')
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    const fetchType = async (ct: string) => {
      const params = new URLSearchParams()
      params.set('content_type', ct)
      if (status !== 'all') params.set('status', status)
      const res = await fetchWithAuth(`/admin/content/review?${params}`)
      return (await res.json()).items || []
    }
    if (type === 'all') {
      Promise.all([fetchType('quiz'), fetchType('lesson')])
        .then(([quizzes, lessons]) => setItems([...quizzes, ...lessons]))
        .catch(err => setError(err.message))
    } else {
      fetchType(type)
        .then(setItems)
        .catch(err => setError(err.message))
    }
  }, [type, status])

  const updateStatus = async (contentType: string, id: string, newStatus: string) => {
    await fetchWithAuth(`/admin/content/${contentType}/${id}/status?status=${newStatus}`, { method: 'PATCH' })
    setItems(prev => prev.map(i => i.id === id ? { ...i, status: newStatus } : i))
  }

  if (error) return <p className="text-red-600">Error: {error}</p>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Content Review</h1>
      <div className="flex gap-4 mb-4">
        <select value={type} onChange={e => setType(e.target.value)} className="border rounded px-3 py-2">
          <option value="all">All Types</option>
          <option value="quiz">Quizzes</option>
          <option value="lesson">Lessons</option>
        </select>
        <select value={status} onChange={e => setStatus(e.target.value)} className="border rounded px-3 py-2">
          <option value="all">All Status</option>
          <option value="draft">Draft</option>
          <option value="published">Published</option>
          <option value="archived">Archived</option>
        </select>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-100">
            <th className="p-2 text-left">Title</th>
            <th className="p-2 text-left">Type</th>
            <th className="p-2 text-left">Grade</th>
            <th className="p-2 text-left">Status</th>
            <th className="p-2 text-left">Created</th>
            <th className="p-2 text-left">Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item: any) => (
            <tr key={item.id} className="border-t">
              <td className="p-2">{item.title || item.topic}</td>
              <td className="p-2">
                <span className={`px-2 py-0.5 rounded text-xs ${item.question_count !== undefined ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'}`}>
                  {item.question_count !== undefined ? 'quiz' : 'lesson'}
                </span>
              </td>
              <td className="p-2">{item.grade_level}</td>
              <td className="p-2">
                <span className={`px-2 py-0.5 rounded text-xs ${
                  item.status === 'published' ? 'bg-green-100 text-green-700' :
                  item.status === 'draft' ? 'bg-yellow-100 text-yellow-700' :
                  'bg-gray-100 text-gray-700'
                }`}>{item.status}</span>
              </td>
              <td className="p-2 text-gray-500">{item.created_at ? new Date(item.created_at).toLocaleDateString() : '-'}</td>
              <td className="p-2 flex gap-2">
                <button
                  onClick={() => {
                    const ct = item.question_count !== undefined ? 'quiz' : 'lesson'
                    router.push(`/admin/content/${ct}/${item.id}`)
                  }}
                  className="text-blue-600 hover:underline text-xs"
                >View</button>
                {item.status !== 'published' && (
                  <button onClick={() => updateStatus(item.question_count !== undefined ? 'quiz' : 'lesson', item.id, 'published')} className="text-green-600 hover:underline text-xs">Publish</button>
                )}
                {item.status === 'published' && (
                  <button onClick={() => updateStatus(item.question_count !== undefined ? 'quiz' : 'lesson', item.id, 'archived')} className="text-red-600 hover:underline text-xs">Archive</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 2: Create quiz detail page**

`dashboard/src/app/admin/content/quiz/[id]/page.tsx`:
```tsx
'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

export default function AdminQuizDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [quiz, setQuiz] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    fetchWithAuth(`/admin/content/quiz/${id}`)
      .then(res => res.json())
      .then(setQuiz)
      .catch(err => setError(err.message))
  }, [id])

  const toggleStatus = async () => {
    const newStatus = quiz.status === 'published' ? 'archived' : 'published'
    await fetchWithAuth(`/admin/content/quiz/${id}/status?status=${newStatus}`, { method: 'PATCH' })
    setQuiz({ ...quiz, status: newStatus })
  }

  if (error) return <p className="text-red-600">Error: {error}</p>
  if (!quiz) return <p className="text-gray-500">Loading...</p>

  return (
    <div>
      <button onClick={() => router.push('/admin/content')} className="text-blue-600 hover:underline mb-4 inline-block">&larr; Back to Content</button>
      <h1 className="text-2xl font-bold mb-4">{quiz.title}</h1>
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div><strong>Grade:</strong> {quiz.grade_level}</div>
        <div><strong>Topic:</strong> {quiz.topic}</div>
        <div><strong>Status:</strong> <span className={`px-2 py-0.5 rounded text-xs ${quiz.status === 'published' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>{quiz.status}</span></div>
        <div><strong>Model:</strong> {quiz.model_used}</div>
        <div><strong>Questions:</strong> {quiz.question_count}</div>
        <div><strong>Created:</strong> {quiz.created_at ? new Date(quiz.created_at).toLocaleDateString() : '-'}</div>
      </div>
      <button onClick={toggleStatus} className={`px-4 py-2 rounded text-white ${quiz.status === 'published' ? 'bg-red-600' : 'bg-green-600'}`}>
        {quiz.status === 'published' ? 'Archive Quiz' : 'Publish Quiz'}
      </button>
      <h2 className="text-xl font-semibold mt-8 mb-4">Questions</h2>
      {quiz.questions?.map((q: any, i: number) => (
        <div key={q.id} className="border rounded p-4 mb-3">
          <p className="font-medium">{i + 1}. {q.question_text}</p>
          <p className="text-sm text-gray-500 mt-1">Type: {q.question_type} | Difficulty: {q.difficulty}</p>
          {q.options?.length > 0 && (
            <ul className="mt-2 space-y-1">
              {q.options.map((opt: string, j: number) => (
                <li key={j} className={`text-sm ${opt === q.correct_answer ? 'text-green-700 font-medium' : ''}`}>
                  {opt === q.correct_answer ? '✓ ' : ''}{opt}
                </li>
              ))}
            </ul>
          )}
          {q.explanation && <p className="text-sm text-gray-600 mt-2 italic">{q.explanation}</p>}
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 3: Create lesson detail page**

`dashboard/src/app/admin/content/lesson/[id]/page.tsx`:
```tsx
'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

export default function AdminLessonDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [lesson, setLesson] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    fetchWithAuth(`/admin/content/lesson/${id}`)
      .then(res => res.json())
      .then(setLesson)
      .catch(err => setError(err.message))
  }, [id])

  const toggleStatus = async () => {
    const newStatus = lesson.status === 'published' ? 'archived' : 'published'
    await fetchWithAuth(`/admin/content/lesson/${id}/status?status=${newStatus}`, { method: 'PATCH' })
    setLesson({ ...lesson, status: newStatus })
  }

  if (error) return <p className="text-red-600">Error: {error}</p>
  if (!lesson) return <p className="text-gray-500">Loading...</p>

  return (
    <div>
      <button onClick={() => router.push('/admin/content')} className="text-blue-600 hover:underline mb-4 inline-block">&larr; Back to Content</button>
      <h1 className="text-2xl font-bold mb-4">{lesson.topic}</h1>
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div><strong>Grade:</strong> {lesson.grade_level}</div>
        <div><strong>Status:</strong> <span className={`px-2 py-0.5 rounded text-xs ${lesson.status === 'published' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>{lesson.status}</span></div>
        <div><strong>Model:</strong> {lesson.model_used}</div>
        <div><strong>Created:</strong> {lesson.created_at ? new Date(lesson.created_at).toLocaleDateString() : '-'}</div>
      </div>
      <button onClick={toggleStatus} className={`px-4 py-2 rounded text-white ${lesson.status === 'published' ? 'bg-red-600' : 'bg-green-600'}`}>
        {lesson.status === 'published' ? 'Archive Lesson' : 'Publish Lesson'}
      </button>
      <div className="mt-6 space-y-4">
        <div><strong>Objective:</strong><p className="mt-1">{lesson.objective}</p></div>
        {lesson.prior_knowledge && <div><strong>Prior Knowledge:</strong><p className="mt-1">{lesson.prior_knowledge}</p></div>}
        {lesson.explanation && <div><strong>Explanation:</strong><p className="mt-1">{lesson.explanation}</p></div>}
        {lesson.activities && <div><strong>Activities:</strong><p className="mt-1 whitespace-pre-wrap">{typeof lesson.activities === 'string' ? lesson.activities : JSON.stringify(lesson.activities)}</p></div>}
        {lesson.assessment && <div><strong>Assessment:</strong><p className="mt-1">{lesson.assessment}</p></div>}
        {lesson.homework && <div><strong>Homework:</strong><p className="mt-1">{lesson.homework}</p></div>}
        {lesson.teacher_notes && <div><strong>Teacher Notes:</strong><p className="mt-1">{lesson.teacher_notes}</p></div>}
      </div>
    </div>
  )
}
```

---

### Task 6: Monitoring, Schools, and Users pages

**Files:**
- Create: `dashboard/src/app/admin/monitoring/page.tsx`
- Create: `dashboard/src/app/admin/schools/page.tsx`
- Create: `dashboard/src/app/admin/users/page.tsx`

- [ ] **Step 1: Create monitoring page**

`dashboard/src/app/admin/monitoring/page.tsx`:
```tsx
'use client'

import { useEffect, useState } from 'react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

export default function AdminMonitoringPage() {
  const [data, setData] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchWithAuth('/admin/monitoring')
      .then(res => res.json())
      .then(setData)
      .catch(err => setError(err.message))
  }, [])

  if (error) return <p className="text-red-600">Error: {error}</p>
  if (!data) return <p className="text-gray-500">Loading...</p>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Model Monitoring</h1>
      <div className="grid grid-cols-3 gap-4">
        <div className="p-4 rounded-lg bg-blue-50">
          <div className="text-2xl font-bold text-blue-700">{data.total_requests}</div>
          <div className="text-sm text-blue-600">Total Requests</div>
        </div>
        <div className="p-4 rounded-lg bg-red-50">
          <div className="text-2xl font-bold text-red-700">{data.failed_requests}</div>
          <div className="text-sm text-red-600">Failed</div>
        </div>
        <div className="p-4 rounded-lg bg-amber-50">
          <div className="text-2xl font-bold text-amber-700">{data.fallback_rate}%</div>
          <div className="text-sm text-amber-600">Fallback Rate</div>
        </div>
      </div>
      {data.fallbacks > 0 && (
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-sm">
          <strong>Fallbacks triggered:</strong> {data.fallbacks} times
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Create schools page**

`dashboard/src/app/admin/schools/page.tsx`:
```tsx
'use client'

import { useEffect, useState } from 'react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

export default function AdminSchoolsPage() {
  const [schools, setSchools] = useState<any[]>([])
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    try {
      const res = await fetchWithAuth('/admin/schools')
      setSchools(await res.json())
    } catch (err: any) {
      setError(err.message)
    }
  }

  useEffect(() => { load() }, [])

  const create = async () => {
    if (!name.trim()) return
    await fetchWithAuth('/teacher/schools', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name.trim() }),
    })
    setName('')
    setShowForm(false)
    load()
  }

  if (error) return <p className="text-red-600">Error: {error}</p>

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Schools</h1>
        <button onClick={() => setShowForm(true)} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
          + Add School
        </button>
      </div>
      {showForm && (
        <div className="mb-4 flex gap-2">
          <input value={name} onChange={e => setName(e.target.value)} placeholder="School name" className="border rounded px-3 py-2 flex-1" autoFocus />
          <button onClick={create} className="bg-green-600 text-white px-4 py-2 rounded text-sm">Save</button>
          <button onClick={() => setShowForm(false)} className="text-gray-500 px-4 py-2 text-sm">Cancel</button>
        </div>
      )}
      <div className="grid gap-4">
        {schools.map((s: any) => (
          <div key={s.id} className="border rounded p-4 bg-white">
            <h3 className="font-semibold">{s.name}</h3>
            <p className="text-sm text-gray-500 mt-1">
              {s.teacher_count ?? '?'} teachers · {s.student_count ?? '?'} students · Grade {s.grade_range ?? 'N/A'}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create users page**

`dashboard/src/app/admin/users/page.tsx`:
```tsx
'use client'

import { useEffect, useState } from 'react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

const ROLES = ['all', 'student', 'teacher', 'parent', 'admin'] as const

export default function AdminUsersPage() {
  const [users, setUsers] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [role, setRole] = useState('all')
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    try {
      const params = new URLSearchParams()
      if (search) params.set('search', search)
      if (role !== 'all') params.set('role', role)
      const res = await fetchWithAuth(`/admin/users?${params}`)
      const data = await res.json()
      setUsers(data.users)
      setTotal(data.total)
    } catch (err: any) {
      setError(err.message)
    }
  }

  useEffect(() => { load() }, [role, search])

  const toggleStatus = async (userId: string, current: boolean) => {
    await fetchWithAuth(`/admin/users/${userId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: !current }),
    })
    load()
  }

  if (error) return <p className="text-red-600">Error: {error}</p>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Users ({total})</h1>
      <div className="flex gap-4 mb-4">
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search by email or telegram_id..." className="border rounded px-3 py-2 flex-1" />
        <div className="flex gap-2">
          {ROLES.map(r => (
            <button key={r} onClick={() => setRole(r)} className={`px-3 py-1 rounded text-sm ${role === r ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}>
              {r === 'all' ? 'All' : r.charAt(0).toUpperCase() + r.slice(1)}
            </button>
          ))}
        </div>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-100">
            <th className="p-2 text-left">Email</th>
            <th className="p-2 text-left">Role</th>
            <th className="p-2 text-left">Grade</th>
            <th className="p-2 text-left">Telegram</th>
            <th className="p-2 text-left">Status</th>
            <th className="p-2 text-left">Created</th>
            <th className="p-2 text-left">Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u: any) => (
            <tr key={u.id} className="border-t">
              <td className="p-2">{u.email ?? '-'}</td>
              <td className="p-2 capitalize">{u.role}</td>
              <td className="p-2">{u.grade_level ?? '-'}</td>
              <td className="p-2 font-mono text-xs">{u.telegram_id ?? '-'}</td>
              <td className="p-2">
                <span className={`px-2 py-0.5 rounded text-xs ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                  {u.is_active ? 'active' : 'inactive'}
                </span>
              </td>
              <td className="p-2 text-gray-500">{u.created_at ? new Date(u.created_at).toLocaleDateString() : '-'}</td>
              <td className="p-2">
                <button onClick={() => toggleStatus(u.id, u.is_active)} className={`text-xs hover:underline ${u.is_active ? 'text-red-600' : 'text-green-600'}`}>
                  {u.is_active ? 'Deactivate' : 'Activate'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

---

### Task 7: Run lint + typecheck and fix issues

- [ ] **Step 1: Run ruff on backend**

Run: `./.venv/bin/ruff check src/api/admin.py src/api/teacher.py`
Expected: No errors

- [ ] **Step 2: Run mypy on backend**

Run: `./.venv/bin/mypy src/api/admin.py src/api/teacher.py`
Expected: No type errors (or pre-existing ones only)

- [ ] **Step 3: Run backend tests**

Run: `./.venv/bin/pytest tests/test_admin_api.py -v`
Expected: All admin API tests pass

- [ ] **Step 4: Typecheck frontend**

Run: `cd dashboard && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 5: Run ruff on full backend**

Run: `./.venv/bin/ruff check src/`
Expected: No new errors

- [ ] **Step 6: Run all backend tests**

Run: `./.venv/bin/pytest tests/ -v -k "not test_chat_endpoint and not test_quiz_generate_endpoint" --tb=short 2>&1 | tail -20`
Expected: 0 new failures (pre-existing 8 failures unchanged)
