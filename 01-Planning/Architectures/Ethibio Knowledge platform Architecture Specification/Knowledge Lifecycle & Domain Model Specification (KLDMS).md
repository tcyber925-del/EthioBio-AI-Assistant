Excellent. This second document is arguably the most important one in the entire subsystem because it defines the **domain model**. If KMAS is the "constitution," then this document defines the "language" that every service, database table, API, frontend component, and agent will speak.

I also want to improve on a traditional domain model.

Instead of modeling **documents**, we're going to model **knowledge**.

---

# Knowledge Lifecycle & Domain Model Specification (KLDMS)

**Version:** 1.0

**Status:** Proposed Architecture

**Depends on:** KMAS v1.0

**Priority:** Platform Critical

---

# 1. Purpose

This specification defines the canonical domain model for all educational knowledge managed by EthioBio AI.

Its objectives are to:

* Establish a unified representation for every educational resource.
* Define lifecycle states from creation to archival.
* Standardize ownership, permissions, metadata, and relationships.
* Decouple knowledge management from storage technologies.
* Provide a stable contract for backend services, frontend applications, retrieval systems, and AI agents.

---

# 2. Design Philosophy

The platform does **not** manage files.

The platform manages **Knowledge Objects**.

A PDF is simply one way to create a Knowledge Object.

Likewise:

* textbook
* lesson plan
* worksheet
* notebook
* exam
* curriculum
* presentation
* scanned image

All become Knowledge Objects.

This abstraction allows the system to evolve without redesigning its core architecture whenever a new content type is introduced.

---

# 3. Core Domain Model

```text
Knowledge Ecosystem

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
        │
        ▼
Knowledge Version
        │
        ▼
Knowledge Asset
        │
        ▼
Knowledge Chunk
```

Each level has a distinct responsibility.

---

# 4. Knowledge Space

A **Knowledge Space** is the highest organizational boundary.

Examples:

```text
Platform Knowledge

Organization Knowledge

Teacher Knowledge

Student Knowledge

Research Knowledge
```

Responsibilities:

* ownership boundary
* security boundary
* retrieval boundary
* scalability boundary

---

# 5. Workspace

A Workspace groups knowledge around a common purpose.

Examples:

```text
Grade 10 Biology

Semester 1

Class 10A

Photosynthesis Unit

School Administration

Personal Study
```

Responsibilities:

* collaboration
* search scope
* permissions
* organization
* lifecycle

A workspace may contain multiple collections.

---

# 6. Collection

Collections organize related knowledge inside a workspace.

Examples:

```text
Lesson Plans

Textbooks

Assignments

Exams

Lab Manuals

Research Papers

Notes

Policies
```

Collections improve discoverability without affecting retrieval semantics.

---

# 7. Knowledge Object

The Knowledge Object is the fundamental entity in the platform.

Every educational resource is represented as a Knowledge Object regardless of its original format.

### Identity

Every object has:

* globally unique identifier
* owner
* workspace
* collection
* source
* creation timestamp
* current version

### Metadata

Administrative metadata:

* filename
* media type
* language
* size
* checksum

Educational metadata:

* subject
* grade
* curriculum
* chapter
* learning objectives
* difficulty
* academic year
* topic hierarchy

Semantic metadata:

* concepts
* keywords
* entities
* prerequisites
* related concepts

Operational metadata:

* processing status
* indexing status
* embedding version
* parser version

---

# 8. Knowledge Version

Knowledge is immutable once published.

Instead of modifying an object, the platform creates a new version.

Benefits:

* reproducibility
* rollback
* auditability
* citation stability
* deterministic evaluation

Version history includes:

* author
* timestamp
* change summary
* processing results

---

# 9. Knowledge Assets

A Knowledge Object may produce multiple derived assets.

Examples:

```text
Original PDF

Extracted Text

OCR Output

Tables

Diagrams

Images

Embeddings

Summaries

Glossary

Flashcards

Generated Questions
```

Assets inherit the lifecycle of their parent object.

---

# 10. Knowledge Chunks

Chunks are retrieval units, not storage units.

Each chunk contains:

* text
* embedding
* lexical index
* metadata
* source reference
* educational annotations

Chunks are never exposed directly to users.

Agents consume them internally.

---

# 11. Educational Metadata Model

Educational metadata is treated as a first-class concern.

Minimum schema:

```text
Subject

Grade

Unit

Chapter

Section

Topic

Learning Objective

Bloom Level

Difficulty

Curriculum Alignment

Assessment Type

Language

Educational Role

Estimated Study Time

Prerequisites
```

Future extensions can add competencies, standards, or regional curriculum mappings without changing the core model.

---

# 12. Knowledge Relationships

Knowledge is not isolated.

The platform maintains explicit relationships.

Relationship types include:

```text
belongs_to

references

extends

summarizes

explains

depends_on

prerequisite_of

aligned_with

contradicts

supersedes

duplicates
```

These relationships enable richer reasoning and graph traversal beyond simple similarity search.

---

# 13. Knowledge Lifecycle

Every Knowledge Object progresses through defined lifecycle states.

```text
Draft
    │
    ▼
Uploaded
    │
    ▼
Validated
    │
    ▼
Registered
    │
    ▼
Processing
    │
    ▼
Enriched
    │
    ▼
Indexed
    │
    ▼
Published
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

### State Definitions

* **Draft** – Object exists only on the client or is being prepared.
* **Uploaded** – Binary received by the server.
* **Validated** – File integrity, type, and security checks complete.
* **Registered** – Metadata persisted and identifier assigned.
* **Processing** – Extraction, OCR, parsing, and analysis underway.
* **Enriched** – Educational metadata and relationships generated.
* **Indexed** – Search indices and embeddings completed.
* **Published** – Available for retrieval.
* **Active** – Actively participating in AI workflows.
* **Archived** – Retained but excluded from normal retrieval.
* **Deleted** – Logically removed while preserving audit requirements where applicable.

---

# 14. Ownership Model

Every Knowledge Object belongs to exactly one owner.

Supported owner types:

```text
Platform

Organization

Teacher

Student

Administrator

System
```

Ownership governs:

* edit permissions
* deletion rights
* sharing
* auditing
* lifecycle transitions

---

# 15. Permission Model

Permissions are applied independently of ownership.

Core roles:

```text
Owner

Editor

Contributor

Viewer

AI Agent
```

Example capabilities:

| Action                 | Owner | Editor | Viewer |            AI Agent           |
| ---------------------- | :---: | :----: | :----: | :---------------------------: |
| View                   |   ✓   |    ✓   |    ✓   |               ✓               |
| Edit metadata          |   ✓   |    ✓   |    ✗   |               ✗               |
| Upload new version     |   ✓   |    ✓   |    ✗   |               ✗               |
| Delete                 |   ✓   |    ✗   |    ✗   |               ✗               |
| Retrieve for reasoning |   ✓   |    ✓   |    ✓   | ✓ (subject to access control) |

AI agents never bypass permissions; they inherit the requesting user's access.

---

# 16. Provenance & Trust

Every Knowledge Object records its origin.

Possible provenance values include:

```text
Platform Curated

Official Curriculum

Teacher Authored

Student Uploaded

AI Generated

Imported

External Web

Research
```

Responses generated by the platform retain provenance through the citation pipeline, enabling users to distinguish between authoritative textbooks, teacher materials, personal notes, and external references.

---

# 17. Lifecycle Events

The domain model exposes lifecycle events rather than tightly coupling components.

Representative events:

```text
KnowledgeRegistered

KnowledgeValidated

KnowledgeProcessingStarted

KnowledgeMetadataExtracted

KnowledgeIndexed

KnowledgePublished

KnowledgeArchived

KnowledgeDeleted

KnowledgeVersionCreated
```

These events allow downstream services—background workers, notification systems, analytics, cache invalidation, and evaluation pipelines—to react without direct dependencies.

---

# 18. Future-Proofing

The domain model is intentionally content-agnostic.

The same abstractions support future knowledge types such as:

* audio lectures
* classroom recordings
* laboratory videos
* interactive simulations
* datasets
* websites
* AI-generated study plans
* collaborative notebooks

No structural changes to the model should be required when these resource types are introduced.

---

# 19. Success Criteria

The domain model is successful when:

* Every educational resource can be represented as a Knowledge Object.
* New content types integrate without redesigning the architecture.
* Knowledge remains traceable through versions, provenance, and relationships.
* AI agents consume a consistent abstraction regardless of storage backend.
* The model supports both today's biology corpus and future multi-subject expansion.
* Permissions and lifecycle rules are enforced consistently across all services.

---

# Review and next step

With **KMAS** and **KLDMS**, we now have:

* **System architecture** (how the platform is organized).
* **Domain language** (what the platform manages).

These two documents define the *what*. The next document should define the *how*:

> **Knowledge Processing Pipeline Specification (KPPS)**

That specification will cover the complete ingestion and processing workflow—from upload through validation, extraction, OCR, educational enrichment, structure-aware chunking, embedding generation, hybrid indexing, relationship extraction, background intelligence (summaries, flashcards, quizzes, glossaries), failure handling, retries, observability, and publication into the Knowledge Management Layer. It will serve as the implementation blueprint for the backend ingestion subsystem.
