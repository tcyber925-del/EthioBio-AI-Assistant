# PRD-A2 — Workspace Service

**Program:** A – Foundation Platform

**Epic:** A2

**Status:** Ready for Implementation

---

# Executive Summary

The Workspace Service provides the contextual boundary for all knowledge managed within EthioBio AI. It governs ownership, organization, permissions, collaboration, and AI context.

A Workspace is **not** a storage folder. It is an educational context that scopes AI retrieval, reasoning, and collaboration.

---

# Goals

* Implement workspace lifecycle management.
* Support personal, teacher, classroom, school, and platform workspaces.
* Manage collections within workspaces.
* Enforce role-based access control (RBAC).
* Provide workspace context for retrieval and reasoning.
* Establish APIs and events for downstream services.

---

# Non-Goals

* File uploads
* Document parsing
* Knowledge indexing
* Search
* Collaboration features beyond membership and permissions

---

# Functional Requirements

## Workspace Lifecycle

Supported states:

```text
Draft
↓
Active
↓
Archived
↓
Deleted
```

Only valid transitions are allowed.

---

## Workspace Types

* Personal
* Teacher
* Classroom
* School
* Platform

The Platform workspace hosts built-in Biology textbooks and future curated educational resources.

---

## Collections

Default collections:

* Textbooks
* Lesson Plans
* Worksheets
* Assignments
* Assessments
* Research
* Student Notes
* Teacher Notes
* Generated Resources
* Media

Collections are organizational only and do not change permissions.

---

## Membership

Roles:

* Owner
* Administrator
* Teacher
* Student
* Editor
* Viewer
* AI Agent

Permissions are inherited unless explicitly overridden.

---

## Workspace Context

Context metadata includes:

* Subject
* Grade
* Curriculum
* Language
* Academic Year
* Semester
* Institution (optional)

This metadata is automatically supplied to retrieval planners.

---

## Sharing

Support:

* Private
* Specific Users
* Classroom
* School
* Organization

---

## Audit

Record:

* Workspace created
* Updated
* Archived
* Deleted
* Member added
* Member removed
* Permission changed
* Collection created
* Collection deleted

---

# Data Model

Workspace

```text
id
name
type
owner_id
status
context
created_at
updated_at
```

Collection

```text
id
workspace_id
name
description
created_at
```

Membership

```text
id
workspace_id
user_id
role
created_at
```

Permission

```text
id
workspace_id
subject
action
effect
```

---

# APIs

Commands

* Create Workspace
* Update Workspace
* Archive Workspace
* Delete Workspace
* Create Collection
* Delete Collection
* Add Member
* Remove Member
* Update Role

Queries

* Get Workspace
* List Workspaces
* Get Collections
* Get Members
* Get Context

---

# Events

Publish

* WorkspaceCreated
* WorkspaceUpdated
* WorkspaceArchived
* WorkspaceDeleted
* CollectionCreated
* CollectionDeleted
* MemberAdded
* MemberRemoved
* PermissionChanged

Consume

* UserCreated
* OrganizationUpdated

---

# Security

* RBAC enforcement
* Workspace isolation
* Permission inheritance
* Audit every permission change

---

# Performance Targets

Workspace lookup: <50 ms

Collection lookup: <50 ms

Membership updates: <100 ms

---

# Testing

* Unit tests
* API tests
* Permission tests
* Integration tests
* Regression tests

---

# Acceptance Criteria

* Workspace lifecycle implemented
* Collection management operational
* RBAC operational
* Context injection available
* APIs documented
* Events published
* Test suite passing

---

# Task Packages

## A2.1

Workspace Domain Models

Deliverables:

* Workspace entity
* Collection entity
* Membership entity
* Permission entity

---

## A2.2

Workspace Repository

Deliverables:

* Persistence layer
* Transactions
* Queries

---

## A2.3

Workspace Service

Deliverables:

* Business logic
* Validation
* Lifecycle

---

## A2.4

REST API

Deliverables:

* Controllers
* DTOs
* Validation
* OpenAPI

---

## A2.5

Authorization Engine

Deliverables:

* RBAC
* Permission inheritance
* Access evaluation

---

## A2.6

Events

Deliverables:

* Publishers
* Consumers
* Event schemas

---

## A2.7

Testing

Deliverables:

* Unit
* Integration
* Contract
* Regression

---

# Definition of Done

* EOS compliant
* Architecture compliant
* APIs documented
* Events documented
* Feature flag implemented
* Metrics added
* Logging added
* CodeRabbit clean
* Human approval complete
