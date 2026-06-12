# Manual Test Plan — Post-Rebuild Verification

**Infrastructure:** App (:8000), Dashboard (:3000), Telegram Bot
**Build:** Commit `1bc27b0` — PRDs 010A-010D + Admin Review

---

## 1. Dashboard — Admin Panel

### 1.1 Admin Dashboard (`/admin`)
- [ ] Navigate to `http://localhost:3000/admin`
- [ ] Verify sidebar shows: Dashboard, Review Queue, Content Review, Schools, Users, Monitoring
- [ ] Verify aggregate cards load: Total Users, Teachers, Students, Parents
- [ ] Verify Recent Users table loads
- [ ] Verify Recent Model Logs table loads

### 1.2 Review Queue (`/admin/review`)
- [ ] Navigate to Review Queue tab
- [ ] Verify Pending tab shows items (with count badge) — empty state "No items pending review" is OK
- [ ] Switch to Resolved tab — verify list or empty state
- [ ] Click a pending item → verify detail panel expands showing: user_message, response, safety issues, safety action, groundedness %, hallucination rate
- [ ] Click **Resolve** button → verify modal opens with textarea
- [ ] Type notes and Confirm → verify item moves to Resolved tab

### 1.3 Content Review (`/admin/content`)
- [ ] Navigate to Content Review
- [ ] Verify quiz/lesson listing loads (filterable by status)
- [ ] Click a quiz → verify detail view (questions, options, correct_answer, difficulty)
- [ ] Click a lesson → verify detail view (objective, prior_knowledge, explanation, activities, assessment)
- [ ] Test Publish/Archive status change

### 1.4 User Management (`/admin/users`)
- [ ] Verify user list loads with pagination
- [ ] Test search by email
- [ ] Test role filter (All/Student/Teacher/Admin/Parent)
- [ ] Test page navigation
- [ ] Test Deactivate/Activate toggle on a user
- [ ] Test Change Role dropdown

### 1.5 Schools (`/admin/schools`)
- [ ] Verify school list loads with teacher_count, student_count, grade_range
- [ ] Verify each school entry renders correctly

### 1.6 Monitoring (`/admin/monitoring`)
- [ ] Verify total requests, failed requests, fallback rate, fallback count load
- [ ] Verify model performance table renders

---

## 2. Dashboard — Student Features

### 2.1 Ask Q&A (`/ask`)
- [ ] Type a biology question (e.g., "What is mitosis?")
- [ ] Verify response includes: answer, language, confidence, sources, model_used
- [ ] Verify gamification fields: xp_awarded, level_up, new_level

### 2.2 Quizzes (`/quizzes`)
- [ ] Generate a new quiz
- [ ] Complete a quiz
- [ ] Verify quiz result page renders with score

### 2.3 Diagrams (`/diagrams`)
- [ ] Generate a diagram
- [ ] Verify SVG renders with labels
- [ ] Test label submission

### 2.4 Recovery Dashboard (`/recovery`)
- [ ] Enter a student UUID
- [ ] Verify weak topics, active plans, completion % load
- [ ] Verify radar chart renders (if ≥3 weak topics)

---

## 3. Telegram Bot

### 3.1 Basic Commands
- [ ] `/start` — Verify registration/welcome flow
- [ ] `/help` — Verify help text
- [ ] `/menu` — Verify main menu
- [ ] `/settings` — Verify settings menu

### 3.2 Agentic RAG Flow
- [ ] Type a complex biology question (e.g., "Explain protein synthesis from DNA to protein") → verify response uses full graph pipeline
- [ ] `/ask What is photosynthesis?` — Verify response includes answer, model_used
- [ ] `/hint` — Verify hint is returned with graph pipeline
- [ ] `/reveal` — Verify full answer is revealed

### 3.3 Gamification
- [ ] Ask a question → verify XP is awarded (check for XP response in reply)
- [ ] `/progress` — Verify progress display with text bar charts
- [ ] `/recovery` — Verify recovery plan/task listing

### 3.4 Quiz Flow
- [ ] `/quiz` — Start a quiz
- [ ] Answer questions → verify scoring
- [ ] Complete quiz → verify results

### 3.5 Edge Cases
- [ ] Send non-biology question → verify safety filter triggers
- [ ] Send empty message → verify graceful handling
- [ ] Rapid-fire questions → verify bot doesn't crash
- [ ] `/cancel` during quiz → verify cancellation works

---

## 4. API Health Check

### 4.1 Core Endpoints
```bash
curl http://localhost:8000/health               # → {"status":"ok"}
curl http://localhost:8000/models                # → list of models
curl http://localhost:8000/models/active         # → active model
curl http://localhost:8000/models/health         # → provider health
```

### 4.2 Admin Endpoints
```bash
curl http://localhost:8000/admin/dashboard       # → summary counts
curl http://localhost:8000/admin/monitoring      # → request stats
curl http://localhost:8000/admin/review          # → review queue
```

### 4.3 Trace Endpoints
```bash
curl http://localhost:8000/traces                # → trace list
curl http://localhost:8000/traces/<id>           # → trace detail
```

---

## 5. Evaluation Pipeline (Optional)

```bash
cd evaluation
python run_all.py --agent               # → agent tests pass
python run_all.py --biology             # → biology benchmarks
python run_all.py --production          # → production checks
python run_all.py --certify             # → certification report
```

---

## Key Things to Watch For

| Area | What to Check |
|------|---------------|
| **Bot latency** | Responses should come within a few seconds (not timeout) |
| **Dashboard content** | No loading spinners stuck indefinitely |
| **Admin auth** | Non-admin users should be rejected from `/admin/*` |
| **XP feedback** | Bot responses include XP award text after each interaction |
| **Graph pipeline** | Complex questions should trigger planning/fanout (not just simple retrieval) |
| **Trace persistence** | After asking a question, check `/traces` endpoint for new records |
| **Review Queue** | After a safety-flagged interaction, check `/admin/review` for pending items |
| **Container logs** | `docker compose logs app --tail 50` — no crash loops or import errors |
