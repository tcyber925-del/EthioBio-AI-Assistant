# PRD-B4 — Educational Metadata Extraction Service

**Program:** B – Knowledge Processing Platform

**Epic:** B4

**Status:** Ready for Implementation

---

# Executive Summary

The Educational Metadata Extraction Service enriches parsed educational content with structured educational metadata that enables intelligent retrieval, curriculum alignment, lesson planning, adaptive learning, and AI reasoning.

Unlike generic document metadata, this service understands educational content.

---

# Goals

* Generate educational metadata.
* Identify concepts and terminology.
* Align content to curriculum.
* Extract learning objectives.
* Generate prerequisite relationships.
* Support multilingual metadata.
* Produce confidence scores.

---

# Metadata Categories

## Document Metadata

* Title
* Author
* Publisher
* Edition
* Language
* Subject
* Grade
* Academic Level

---

## Curriculum Metadata

* Curriculum Standard
* Unit
* Chapter
* Topic
* Subtopic
* Learning Objectives

---

## Educational Metadata

* Key Concepts
* Keywords
* Definitions
* Important Facts
* Examples
* Exercises
* Diagrams
* Assessment Items

---

## Learning Metadata

* Bloom's Taxonomy Level
* Difficulty
* Estimated Study Time
* Prerequisites
* Success Criteria

---

## AI Metadata

* Confidence
* Source Reliability
* Citation Quality
* Extraction Version

---

# Pipeline

```text
Normalized Document
        ↓
Language Detection
        ↓
Subject Detection
        ↓
Curriculum Alignment
        ↓
Concept Extraction
        ↓
Learning Objective Detection
        ↓
Bloom Classification
        ↓
Difficulty Estimation
        ↓
Knowledge Graph Candidate Extraction
        ↓
MetadataGenerated Event
```

---

# Functional Requirements

Generate:

* Educational concepts
* Scientific terms
* Biological entities
* Learning objectives
* Glossary entries
* Chapter summaries
* Topic summaries
* Curriculum mappings

Every extracted item includes a confidence score.

---

# APIs

Internal only.

---

# Events

Publish

* MetadataExtractionStarted
* MetadataGenerated
* MetadataUpdated
* MetadataFailed

Consume

* ParsingCompleted

---

# Performance

Metadata generation should execute asynchronously and support parallel processing.

---

# Testing

* Curriculum alignment
* Biology terminology
* Confidence validation
* Multilingual support
* Regression corpus

---

# Acceptance Criteria

✓ Educational metadata generated

✓ Learning objectives extracted

✓ Curriculum alignment available

✓ Confidence scoring implemented

✓ Events published

✓ Tests passing

---

# Task Packages

B4.1 Language Detection

B4.2 Curriculum Alignment

B4.3 Concept Extraction

B4.4 Learning Objective Engine

B4.5 Bloom Classifier

B4.6 Metadata Repository

B4.7 Events

B4.8 Testing

---

# Definition of Done

* Metadata engine operational
* Educational metadata persisted
* APIs documented
* Tests passing
