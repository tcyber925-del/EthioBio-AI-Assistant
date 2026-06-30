# PRD-B7 — Hybrid Indexing Service

**Program:** B – Knowledge Processing Platform

**Epic:** B7

**Status:** Ready for Implementation

---

# Executive Summary

The Hybrid Indexing Service builds the searchable knowledge layer by combining semantic vector indexes with structured lexical indexes and metadata indexes.

This service enables fast, accurate, explainable retrieval across educational content.

---

# Goals

* Create semantic indexes.
* Create lexical indexes.
* Create metadata indexes.
* Support incremental indexing.
* Enable future hybrid ranking strategies.

---

# Index Types

Semantic

* Dense vectors

Lexical

* BM25
* Keyword
* Phrase

Metadata

* Subject
* Grade
* Curriculum
* Chapter
* Topic
* Difficulty
* Language
* Workspace

---

# Pipeline

```text
Embeddings
      ↓
Metadata
      ↓
Lexical Index
      ↓
Vector Index
      ↓
Metadata Index
      ↓
Consistency Validation
      ↓
KnowledgeIndexed
```

---

# Functional Requirements

Support:

* Initial indexing
* Incremental indexing
* Re-indexing
* Partial indexing
* Version-aware indexing

---

# Validation

Verify:

* Missing vectors
* Missing metadata
* Broken references
* Duplicate entries

---

# APIs

Internal only.

Commands

* Index Knowledge
* Rebuild Index
* Remove Index

Queries

* Index Status
* Statistics

---

# Events

Publish

* IndexingStarted
* IndexingCompleted
* IndexingFailed

Consume

* EmbeddingGenerated

---

# Performance

Parallel indexing.

Background processing.

Incremental updates.

---

# Testing

* Incremental indexing
* Full rebuild
* Index validation
* Performance testing
* Regression corpus

---

# Acceptance Criteria

✓ Hybrid indexes created

✓ Incremental indexing operational

✓ Metadata indexed

✓ Validation operational

✓ Tests passing

---

# Task Packages

B7.1 Vector Indexer

B7.2 Lexical Indexer

B7.3 Metadata Indexer

B7.4 Validation

B7.5 Events

B7.6 Testing

---

# Definition of Done

* Hybrid indexing operational
* Validation complete
* Tests passing
* Documentation updated
