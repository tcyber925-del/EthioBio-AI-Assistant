# PRD-A1 — Knowledge Registry & Lifecycle Service

## Status

Ready for Implementation

---

# Goal

Create the canonical registry responsible for every Knowledge Object managed by EthioBio AI.

---

# Responsibilities

* Register Knowledge Objects
* Lifecycle Management
* Metadata
* Versioning
* Provenance
* Relationships
* Registry APIs
* Registry Events

---

# Non-Goals

* OCR
* Upload Processing
* Chunking
* Embeddings
* Search
* Retrieval

---

# Functional Requirements

## Knowledge Registration

Generate globally unique ID.

Persist metadata.

Associate Workspace.

Associate Collection.

Initialize lifecycle.

Emit event.

---

## Lifecycle

States

```
Draft

↓

Uploaded

↓

Validated

↓

Registered

↓

Processing

↓

Enriched

↓

Indexed

↓

Published

↓

Active

↓

Archived

↓

Deleted
```

Transitions validated by state machine.

---

## Versioning

Immutable versions.

Rollback via references.

Complete audit history.

---

## Provenance

Track

* Creator
* Owner
* Source
* Import Method
* Processing History
* Created
* Updated

---

## Relationships

Support

* references
* prerequisite_of
* aligned_with
* supersedes
* duplicate_of

---

# Data Model

KnowledgeObject

```
id
workspace_id
collection_id
owner_id
state
metadata
provenance
current_version
created_at
updated_at
```

KnowledgeVersion

```
id
knowledge_object_id
version
checksum
embedding_version
parser_version
created_at
```

KnowledgeRelationship

```
id
source
target
relationship
confidence
```

---

# APIs

Commands

* Register
* Archive
* Restore
* Delete
* Update Metadata
* Create Version

Queries

* Get Knowledge
* List Knowledge
* Get Version
* Get Lifecycle
* Get Relationships

---

# Events

Publish

* KnowledgeRegistered
* MetadataUpdated
* VersionCreated
* LifecycleChanged
* Archived
* Deleted

Consume

* UploadCompleted
* ParsingCompleted
* IndexingCompleted
* PublicationCompleted

---

# Integration

Workspace Service

Processing Pipeline

Retrieval Gateway

Citation Service

Memory Service

---

# Performance

Registration

<100 ms

Read

<50 ms

Update

<150 ms

---

# Security

Workspace isolation.

RBAC.

Audit every mutation.

---

# Testing

Unit

Integration

Lifecycle

API

Migration

Performance

Regression

---

# Migration

Register existing Biology textbook corpus.

Maintain existing embeddings.

Maintain retrieval compatibility.

---

# Acceptance Criteria

✓ Registry operational

✓ Lifecycle operational

✓ Versioning operational

✓ APIs operational

✓ Events operational

✓ Existing corpus migrated

✓ Regression tests passing

---

# Implementation Task Packages

### A1.1

Domain Models

Files

```
backend/domain/knowledge/
```

Deliverables

* KnowledgeObject
* Version
* Relationship
* Metadata

---

### A1.2

Repository Layer

Deliverables

Repositories

Persistence

Transactions

---

### A1.3

Lifecycle Engine

Deliverables

State Machine

Validation

Transition Rules

---

### A1.4

Registry Service

Deliverables

Application Services

Commands

Queries

---

### A1.5

REST API

Deliverables

Controllers

DTOs

Validation

OpenAPI

---

### A1.6

Events

Deliverables

Publishers

Consumers

Schemas

---

### A1.7

Testing

Deliverables

Unit

Integration

Contract

Migration

Regression

---

# Definition of Done

* Architecture compliant
* EOS compliant
* Tests >90% coverage (Registry module)
* API documented
* Events documented
* Feature flag implemented
* Metrics added
* Logging added
* CodeRabbit clean
* Human approval complete
