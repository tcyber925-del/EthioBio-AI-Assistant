# PRD-B6 — Embedding Generation Service

**Program:** B – Knowledge Processing Platform

**Epic:** B6

**Status:** Ready for Implementation

---

# Executive Summary

The Embedding Generation Service converts validated educational chunks into vector representations for semantic retrieval.

The service is model-agnostic and supports embedding versioning, batch processing, re-embedding, and future model upgrades without requiring document reprocessing.

---

# Goals

* Generate embeddings for every searchable chunk.
* Support multiple embedding providers.
* Track embedding versions.
* Enable incremental re-embedding.
* Optimize throughput through batching.
* Ensure deterministic processing.

---

# Supported Providers

Initial:

* OpenAI
* Local embedding models

Future:

* Voyage AI
* Jina AI
* Nomic
* Instructor
* BGE
* E5
* Custom institutional models

---

# Processing Pipeline

```text
Validated Chunks
        ↓
Batch Builder
        ↓
Embedding Provider
        ↓
Vector Validation
        ↓
Embedding Repository
        ↓
EmbeddingGenerated
```

---

# Functional Requirements

Generate embeddings for:

* Document chunks
* Definitions
* Examples
* Exercises
* Tables
* Figure descriptions
* Glossary entries
* Learning objectives

---

# Versioning

Track:

* Provider
* Model
* Model version
* Embedding dimension
* Generation timestamp

Older embeddings remain available until migration completes.

---

# Batch Processing

Support:

* Configurable batch sizes
* Retry
* Partial batch recovery
* Rate limiting
* Parallel workers

---

# Validation

Verify:

* Vector dimension
* Null vectors
* Duplicate vectors
* Generation failures

---

# APIs

Internal only.

Commands

* Generate Embeddings
* Regenerate Embeddings

Queries

* Embedding Status
* Provider Information

---

# Events

Publish

* EmbeddingStarted
* EmbeddingGenerated
* EmbeddingFailed
* EmbeddingMigrated

Consume

* ChunkingCompleted

---

# Performance

Parallel generation.

Support large textbook batches.

---

# Testing

* Provider abstraction
* Batch processing
* Retry logic
* Version migration
* Performance benchmarking

---

# Acceptance Criteria

✓ Embeddings generated

✓ Versioning operational

✓ Batch processing operational

✓ Validation complete

✓ Tests passing

---

# Task Packages

B6.1 Provider Interface

B6.2 Batch Engine

B6.3 Embedding Generator

B6.4 Validation

B6.5 Repository

B6.6 Events

B6.7 Testing

---

# Definition of Done

* Provider abstraction complete
* Versioning implemented
* Tests passing
* Documentation updated
