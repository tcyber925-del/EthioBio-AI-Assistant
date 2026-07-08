Excellent. We now move to the third and final foundational architecture project.

This is the component that transforms EthioBio from a memory platform into a reasoning platform.

After this PRD, we will have completed the foundational intelligence triangle:

```text
Educational Memory Layer
          +
Educational Event Bus
          +
Educational Knowledge Graph
```

Everything after this becomes an intelligence application built on top of these foundations.

---

# PRD-003 — Educational Knowledge Graph (EKG)

**Project:** EthioBio AI Platform
**Status:** Approved & Implemented (As-Built)
**Priority:** CRITICAL
**Type:** Core Intelligence Architecture
**Dependencies:**

* PRD-001 Unified Educational Memory Layer
* PRD-002 Educational Event Bus

---

# Executive Summary

The Educational Knowledge Graph (EKG) is the central reasoning layer of EthioBio.

Unlike traditional databases that store isolated records, the Knowledge Graph stores educational relationships.

The graph enables the platform to understand:

* How concepts relate
* How students learn
* How misconceptions spread
* How interventions affect outcomes
* How curriculum objectives connect

The graph becomes the reasoning engine behind Teacher Copilot, Misconception Intelligence, Adaptive Planning, and Digital Twins.

---

# Problem Statement

Current educational systems primarily answer:

> What happened?

Examples:

```text
Student scored 65%

Student readiness is 0.72

Student failed Genetics
```

But teachers need answers to:

```text
Why?

What caused it?

What is connected?

What should happen next?
```

Traditional relational systems struggle to answer these efficiently.

---

# Vision

Build a graph that models the educational ecosystem.

Example:

```text
Student
 ↓
struggles_with
 ↓
Genetics

Genetics
 ↓
depends_on
 ↓
Cell Division

Cell Division
 ↓
has_misconception
 ↓
DNA only exists during reproduction
```

The system can reason across relationships rather than isolated records.

---

# Goals

## Primary Goals

Model educational relationships.

Support graph-based reasoning.

Enable teacher explanations.

Power recommendation systems.

Support future simulation systems.

---

## Secondary Goals

Improve RAG quality.

Improve intervention selection.

Improve curriculum navigation.

Improve adaptive planning.

---

# Non-Goals

This project will NOT:

Build Teacher Copilot.

Build Digital Twin.

Build School Intelligence.

Generate recommendations directly.

The graph provides intelligence infrastructure.

---

# Educational Graph Model

The graph consists of:

## Entities

Nodes

## Relationships

Edges

## Properties

Metadata

---

# Core Entity Types

---

## Student

Represents learners.

Example:

```text
Student: Hana
```

Properties:

```text
grade
classroom
mastery
readiness
risk_level
```

---

## Teacher

Represents educators.

Properties:

```text
subjects
preferences
classrooms
```

---

## Classroom

Represents learning groups.

Properties:

```text
grade
subject
student_count
```

---

## Topic

Represents curriculum topics.

Examples:

```text
Cell Biology

Genetics

Ecology
```

---

## Learning Objective

Represents curriculum objectives.

Examples:

```text
Explain photosynthesis

Identify cell structures
```

---

## Assessment

Represents evaluations.

---

## Intervention

Represents instructional actions.

---

## Misconception

Represents incorrect mental models.

Examples:

```text
Respiration only occurs in lungs

Plants do not respire
```

---

## Strategy

Represents instructional techniques.

Examples:

```text
Retrieval Practice

Diagram Learning

Peer Tutoring
```

---

# Core Relationship Types

---

## Curriculum Relationships

### depends_on

```text
Genetics
 ↓
depends_on
 ↓
Cell Division
```

---

### prerequisite_for

```text
Cell Structure
 ↓
prerequisite_for
 ↓
Cell Biology
```

---

## Learning Relationships

### mastered

```text
Student
 ↓
mastered
 ↓
Photosynthesis
```

---

### struggles_with

```text
Student
 ↓
struggles_with
 ↓
Genetics
```

---

### improving_in

```text
Student
 ↓
improving_in
 ↓
Ecology
```

---

## Misconception Relationships

### has_misconception

```text
Student
 ↓
has_misconception
 ↓
Respiration Misconception
```

---

### misconception_about

```text
Misconception
 ↓
misconception_about
 ↓
Cellular Respiration
```

---

## Intervention Relationships

### improved

```text
Intervention
 ↓
improved
 ↓
Mastery
```

---

### reduced

```text
Intervention
 ↓
reduced
 ↓
Risk
```

---

## Teacher Relationships

### teaches

```text
Teacher
 ↓
teaches
 ↓
Classroom
```

---

### prefers

```text
Teacher
 ↓
prefers
 ↓
Strategy
```

---

# Graph Architecture

## Recommended Approach

### Named Adjacency Tables in PostgreSQL

Use:

```text
PostgreSQL
     +
Named Adjacency Tables
```

Instead of a generic Graph Abstraction Layer, each relationship type gets its own well-named table with foreign keys:

```text
topic_prerequisites
  (topic_id, prerequisite_topic_id)

student_misconceptions
  (student_id, misconception_id, confidence)

intervention_outcomes
  (intervention_id, student_id, effectiveness_score)

topic_misconceptions
  (topic_id, misconception_id, severity)
```

Prerequisite chain traversal uses PostgreSQL recursive CTEs, not a graph query language. This approach is more self-documenting, more performant for the known query patterns, and avoids generic graph infrastructure before query patterns validate the need.

Initially avoid deploying:

```text
Neo4j
TigerGraph
JanusGraph
Generic Graph Abstraction Layer
```

unless new query patterns emerge that recursive CTEs cannot handle.

---

# Core Components

---

## Component 1

Relationship Builder

Responsibilities:

Create relationship records in named adjacency tables.

Update relationship state.

Location:

```text
src/core/knowledge_graph/builder/
```

---

## Component 2

Graph Reasoning Engine

Responsibilities:

Answer relationship questions using recursive CTEs.

Examples:

```text
Why is student struggling?

Which prerequisite is weak?

Which misconception causes failure?
```

Location:

```text
src/core/knowledge_graph/reasoning/
```

---

## Component 3

Graph Query Engine

Responsibilities:

Educational graph search via recursive CTEs and join queries.

Example:

```text
WITH RECURSIVE prereq_tree AS (
    SELECT prerequisite_topic_id
    FROM topic_prerequisites
    WHERE topic_id = 'Genetics'
    UNION
    SELECT tp.prerequisite_topic_id
    FROM topic_prerequisites tp
    JOIN prereq_tree pt ON tp.topic_id = pt.prerequisite_topic_id
)
SELECT * FROM prereq_tree;
```

---

## Component 4

Graph Update Subscriber

Consumes events from:

PRD-002 Event Bus.

Example:

```text
AssessmentCompleted

MasteryImproved

MisconceptionDetected
```

Automatically updates graph.

---

# Reasoning Capabilities

---

## Root Cause Analysis

Teacher asks:

> Why is Hana struggling in Genetics?

Graph discovers:

```text
Genetics
 ↓
depends_on
 ↓
Cell Division

Cell Division
 ↓
mastery = low
```

Answer:

> Genetics difficulties are primarily linked to weak Cell Division understanding.

---

## Misconception Analysis

Teacher asks:

> What misconception is affecting most students?

Graph returns:

```text
72%
Respiration only occurs in lungs
```

---

## Intervention Selection

Teacher asks:

> What worked previously?

Graph identifies:

```text
Retrieval Practice

Success Rate: 81%
```

for similar students.

---

# Graph APIs

---

## Create Entity

```typescript
createEntity()
```

---

## Create Relationship

```typescript
createRelationship()
```

---

## Query Graph

```typescript
queryGraph()
```

---

## Explain Relationship

```typescript
explain()
```

---

## Find Similar Entities

```typescript
findSimilar()
```

---

# Teacher Intelligence Integration

The graph becomes the reasoning layer behind:

```text
Teacher Copilot
```

Example:

```text
Teacher:
Why is readiness dropping?

Graph:
Find related topics
Find misconceptions
Find interventions
Generate explanation
```

---

# Memory Integration

Graph consumes:

```text
Semantic Memory

Consolidated Memory

Vector Memory
```

from UEML.

---

# Event Integration

Graph updates from:

```text
AssessmentCompleted

MasteryImproved

RiskDetected

MisconceptionDetected

InterventionCompleted
```

events.

---

# Dashboard Requirements

Graph Explorer.

Relationship Viewer.

Curriculum Dependency Viewer.

Misconception Maps.

Intervention Maps.

---

# Success Metrics

## Technical

Graph query latency <500ms.

Relationship accuracy >95%.

Automatic graph updates >99%.

---

## Product

Improved teacher explanations.

Improved intervention recommendations.

Improved curriculum reasoning.

Improved copilot responses.

---

# Future Features Unlocked

Immediately enables:

### PRD-004

Teacher Copilot

---

### PRD-005

Misconception Intelligence Engine

---

### PRD-006

Intervention Effectiveness Analytics

---

### PRD-007

AI Lesson Planner

---

### PRD-010

Classroom Digital Twin

---

# Implementation Phases

## Phase 1

Graph Foundation

* Entities
* Relationships
* Query APIs

---

## Phase 2

Curriculum Graph

* Topic dependencies
* Learning objectives
* Prerequisites

---

## Phase 3

Student Intelligence Graph

* Mastery
* Misconceptions
* Risk

---

## Phase 4

Intervention Intelligence

* Outcomes
* Effectiveness
* Recommendations

---

# Recommended Next PRD

Now that the foundational architecture is complete, the next project should be the first intelligence application built on top of it:

## PRD-004 — Teacher Copilot

This should become the primary interface to the entire EthioBio intelligence platform and the centerpiece of the teacher experience. It will leverage the Memory Layer, Event Bus, and Knowledge Graph simultaneously, making it the highest-ROI user-facing feature in the roadmap.
