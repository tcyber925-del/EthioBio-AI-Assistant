# PRD-D1 — Workspace Dashboard

**Program:** D – Knowledge Workspace

**Epic:** D1

**Status:** Ready for Implementation

---

# Executive Summary

The Workspace Dashboard is the landing experience for every authenticated user.

It provides a personalized overview of workspaces, recent activity, uploads, collections, AI usage, processing status, and educational insights.

---

# Goals

* Personalized dashboard
* Workspace overview
* Activity tracking
* Quick actions
* Educational insights

---

# Dashboard Sections

## Header

Workspace selector

Search

Notifications

Profile

Quick Upload

---

## Overview Cards

Active Documents

Collections

Uploads

Published Knowledge

Pending Processing

Storage Usage

---

## Recent Activity

Uploads

Edits

Processing

Searches

Lesson Plans

AI Sessions

---

## Processing Status

Queued

Parsing

Metadata

Embedding

Publishing

Failures

---

## AI Assistant

Recent conversations

Suggested study materials

Suggested lesson plans

Recommended uploads

---

## Quick Actions

Upload Material

Create Collection

Search Knowledge

Create Lesson Plan

Generate Quiz

Browse Knowledge

---

## Insights

Most viewed documents

Frequently searched topics

Popular collections

Processing trends

---

# Widgets

Support configurable widgets.

Users may rearrange dashboard.

---

# APIs

GET /dashboard

GET /activity

GET /insights

---

# Events

Consume

WorkspaceUpdated

KnowledgePublished

ProcessingCompleted

---

# Performance

Dashboard load

<300 ms

---

# Testing

Dashboard rendering

Widgets

Permissions

Responsive layout

Accessibility

Regression

---

# Acceptance Criteria

✓ Dashboard operational

✓ Widgets configurable

✓ Insights displayed

✓ Responsive

✓ Tests passing

---

# Task Packages

D1.1 Dashboard Layout

D1.2 Widget Framework

D1.3 Activity Feed

D1.4 Insights

D1.5 Dashboard API

D1.6 Testing

---

# Definition of Done

Dashboard complete

Responsive

Accessible

Tests passing
