Excellent. I think this is the final architecture document before we transition into implementation PRDs.

The previous four documents established:

* **KMAS** → Overall platform architecture
* **KLDMS** → Domain model
* **KPPS** → Knowledge processing pipeline
* **KROS** → Retrieval orchestration

One major subsystem remains undefined:

> **How users organize, share, collaborate on, and govern knowledge.**

This document is not just about folders. It defines the operational model of the platform.

I also want to introduce one improvement over our earlier discussions:

> **The Workspace should not be treated as storage. It should be treated as a bounded educational context.**

This is an important distinction.

A Workspace is where AI understands:

* who is working
* what they're working on
* what knowledge is relevant
* what permissions apply
* what context should influence reasoning

---

# Knowledge Workspace & Collaboration Architecture Specification (KWCAS)

**Version:** 1.0

**Status:** Approved & Implemented (As-Built)

**Depends on:**

* KMAS
* KLDMS
* KPPS
* KROS

**Priority:** Platform Critical

---

# 1. Purpose

The Workspace subsystem provides the organizational, collaborative, and contextual foundation for all user-managed knowledge.

Rather than serving as simple document storage, a Workspace represents an educational context within which knowledge, AI interactions, permissions, and collaboration are coordinated.

The subsystem enables:

* organization of knowledge,
* contextual AI reasoning,
* secure collaboration,
* role-based access,
* version governance,
* scalable multi-tenancy.

---

# 2. Architectural Philosophy

A Workspace is **not** a folder.

A Workspace is **not** a project.

A Workspace is a **bounded educational context**.

Within that context the AI understands:

* educational goals,
* active curriculum,
* participants,
* permissions,
* relevant knowledge,
* historical interactions.

This allows every retrieval and reasoning workflow to become context-aware without requiring repeated user instructions.

---

# 3. Workspace Hierarchy

The hierarchy is intentionally shallow to reduce complexity while remaining extensible.

```text
Knowledge Space
        │
        ▼
Workspace
        │
        ▼
Collection
        │
        ▼
Knowledge Object
```

Responsibilities:

* **Knowledge Space** – security and ownership boundary.
* **Workspace** – contextual boundary.
* **Collection** – organizational boundary.
* **Knowledge Object** – information boundary.

---

# 4. Workspace Types

The platform supports several workspace categories.

## Personal Workspace

Owned by one user.

Examples:

* Study Notes
* Biology Revision
* Research Reading

Characteristics:

* private by default
* personalized AI context
* learner memory integration

---

## Teacher Workspace

Owned by an educator.

Examples:

* Grade 10 Biology
* Semester II
* Lesson Planning

Contains:

* lesson plans
* worksheets
* assessments
* presentations
* teaching notes

---

## Classroom Workspace

Shared by teachers and students.

Contains:

* assignments
* class resources
* announcements
* submissions
* discussions (future)

---

## School Workspace

Organization-wide.

Contains:

* policies
* academic calendar
* staff resources
* curriculum
* regulations

---

## Platform Workspace

Read-only.

Contains:

* official textbooks
* built-in diagrams
* curated educational datasets

This is the home of your existing Biology corpus.

---

## Future Workspace Types

The model should support future additions without redesign:

* District Workspace
* Ministry Workspace
* Research Workspace
* Public Community Workspace

---

# 5. Workspace Context

Every workspace maintains contextual metadata that guides AI behavior.

Examples:

```yaml
Subject:
Biology

Grade:
10

Curriculum:
National

Language:
English

Academic Year:
2026

Semester:
1

Institution:
(Optional)

Teaching Style:
(Optional)

Learning Objectives:
(Optional)
```

This context is injected automatically into retrieval planning and reasoning where appropriate.

---

# 6. Collections

Collections provide lightweight organization.

Suggested default collections:

```text
Textbooks

Lesson Plans

Worksheets

Assignments

Assessments

Presentations

Research

Student Notes

Teacher Notes

Policies

Media

Generated Resources
```

Collections are organizational only; they do not alter security or retrieval semantics.

---

# 7. Membership Model

Every workspace maintains explicit membership.

Roles:

```text
Owner

Administrator

Teacher

Student

Editor

Viewer

AI Agent
```

Permissions are inherited unless explicitly overridden.

---

# 8. Collaboration Model

The platform supports collaborative knowledge creation.

Capabilities include:

* shared uploads
* collaborative editing (future)
* comments (future)
* review workflows (future)
* version approval (future)

Knowledge remains attributable to individual contributors through provenance records.

---

# 9. AI Context Model

When a request originates from a workspace, the AI automatically receives contextual signals.

For example:

Workspace:

```text
Grade 10 Biology
```

User asks:

> Create tomorrow's lesson.

The planner already knows:

* Grade 10
* Biology
* National curriculum
* Semester
* Teacher workspace
* Available lesson plans
* Existing assessments

No repeated prompting is required.

---

# 10. Workspace Lifecycle

Every workspace progresses through lifecycle states.

```text
Draft
    │
    ▼
Active
    │
    ▼
Archived
    │
    ▼
Deleted
```

Definitions:

* **Draft** – being configured.
* **Active** – available for collaboration and AI.
* **Archived** – read-only, excluded from default retrieval.
* **Deleted** – logically removed according to retention policies.

---

# 11. Sharing Model

Sharing is explicit and role-based.

Supported scopes:

```text
Private

Specific Users

Classroom

School

Organization

Public (Future)
```

Sharing modifies access without changing ownership.

---

# 12. Retrieval Scope

Workspaces act as retrieval boundaries.

When a request originates inside a workspace:

1. Search current workspace.
2. Search linked workspaces (if permitted).
3. Search organization knowledge.
4. Search platform knowledge.
5. Search memory.
6. Search external sources (if required).

This keeps retrieval relevant while respecting permissions.

---

# 13. Workspace Relationships

Workspaces can reference one another.

Examples:

```text
School Workspace
        │
        ▼
Classroom Workspace
        │
        ▼
Teacher Workspace
        │
        ▼
Personal Workspace
```

Relationships allow knowledge sharing without duplication.

---

# 14. Quotas & Resource Governance

To support future SaaS deployment, define governance policies now.

Examples:

* maximum workspace count
* storage quotas
* document limits
* concurrent processing jobs
* API rate limits
* archival policies

These should be configurable rather than hardcoded.

---

# 15. Audit & Provenance

Every significant workspace action generates an audit event.

Examples:

* workspace created
* member added
* permissions changed
* document uploaded
* collection modified
* workspace archived

Audit records support compliance, debugging, and institutional governance.

---

# 16. Multi-Tenancy

The architecture should support isolated organizations.

```text
Organization A
    ├── School A1
    ├── School A2

Organization B
    ├── School B1
```

Isolation requirements:

* separate permissions
* separate quotas
* separate audit logs
* optional isolated storage
* configurable retrieval boundaries

This enables future deployment for districts, ministries, or private institutions.

---

# 17. Integration with Existing Architecture

The Workspace subsystem integrates as follows:

* **Knowledge Registry** stores workspace ownership and relationships.
* **Knowledge Processing Pipeline** assigns uploaded Knowledge Objects to workspaces and collections during registration.
* **Retrieval Gateway** uses workspace context to scope searches before querying broader knowledge layers.
* **Memory System** maintains workspace-aware conversational context.
* **Graph Engine** consumes workspace metadata as part of planning and reasoning.

No existing ingestion or retrieval component needs direct knowledge of storage layout; they interact through workspace abstractions.

---

# 18. Success Criteria

The Workspace architecture is successful when it:

* Organizes knowledge around educational context rather than storage.
* Enables collaboration without compromising ownership or provenance.
* Provides consistent permission enforcement across all AI workflows.
* Automatically supplies contextual information to planners and retrieval.
* Scales from individual learners to national educational deployments without redesign.
* Supports future collaboration features through stable architectural contracts.

---

# 19. Architectural Innovation: Context-Centric AI

Most AI platforms organize information by **files** or **projects**.

This architecture organizes information by **educational context**.

The operational flow becomes:

```text
User
    │
    ▼
Workspace Context
    │
    ▼
Intent Analysis
    │
    ▼
Retrieval Planning
    │
    ▼
Evidence Package
    │
    ▼
Reasoning
    │
    ▼
Grounded Educational Response
```

This means context is established **before** retrieval begins, reducing prompt complexity and improving consistency across tutoring, lesson planning, assessment generation, classroom management, and school administration.

---

# Architecture Phase Complete

At this point, we've completed a coherent architecture suite:

1. **KMAS** — Knowledge Management Architecture
2. **KLDMS** — Knowledge Lifecycle & Domain Model
3. **KPPS** — Knowledge Processing Pipeline
4. **KROS** — Knowledge Retrieval & Orchestration
5. **KWCAS** — Knowledge Workspace & Collaboration

Together, these define the platform's knowledge subsystem from organization and governance through processing, retrieval, and AI reasoning.

---

# 20. As-Built Workspace Collaboration Reference (As of July 2026 Implementation)

During execution, the workspace collaboration concepts were implemented with the following specifications:

### 20.1 Workspace Context Header (`X-Workspace-Id`)
To prevent token-refresh latency when teachers switch between classrooms, the workspace identity context is passed as a standalone HTTP header `X-Workspace-Id` instead of embedding it directly in the user's JWT. The frontend client library intercepts calls and injects this header automatically from local storage state variables.

### 20.2 Classroom Binding & Seeding
The new `workspaces` table contains a nullable `class_group_id` foreign key mapped to the existing `ClassGroup` schema. Seeding logic parses `ClassGroup` values to automatically establish the primary classroom workspace and populate member roles.

### 20.3 Local Storage Platform MVP
Raw documents uploaded to workspaces are stored on the local filesystem grouped securely under `./data/storage/{workspace_id}/{ko_id}/{filename}`. A unified `StorageAdapter` interface mediates file access, providing clean migration pathways to AWS S3 or MinIO.

