# Feature PRD — Gamification System

## Project
EthioSci AI Assistant

## Branch
feature/gamification-system

---

# Overview

Implement a gamified biology learning experience using:
- XP,
- mastery levels,
- streaks,
- achievements,
- progress tracking,
- contextual learning rewards.

The system should increase:
- motivation,
- retention,
- study consistency,
- quiz completion,
- long-term engagement.

Gamification must be integrated directly into the learning experience rather than isolated into a separate page.

---

# Goals

- Encourage daily biology study habits
- Increase quiz completion rates
- Reward active participation
- Improve long-term retention
- Reinforce positive learning behavior
- Make progression visible and motivating

---

# Non-Goals

- Competitive multiplayer systems
- Public global leaderboards
- Real-money rewards
- Social networking features
- NFT/blockchain mechanics
- Complex virtual economies

---

# Gamification Philosophy

The system should:
- reward learning behaviors,
- reinforce consistency,
- encourage mastery,
- support struggling students,
- avoid addictive or manipulative mechanics.

Rewards should feel:
- educational,
- meaningful,
- motivating,
- lightweight,
- non-intrusive.

---

# Core Mechanics

## XP (Experience Points)

XP is awarded for:
- quiz completion,
- correct answers,
- Socratic tutoring participation,
- streak continuation,
- recovery-plan completion,
- mastering weak topics,
- completing visual diagram exercises.

XP is the primary progression currency.

---

## Streak System

Tracks consecutive study days.

Actions that maintain streaks:
- completing quizzes,
- tutoring sessions,
- recovery tasks,
- diagram activities.

Missing a full day resets the streak.

---

## Mastery Levels

Represents student biology competency progression.

Levels are determined by:
- accumulated XP,
- topic mastery,
- recovery progress.

Example:
- Level 1 → Biology Beginner
- Level 5 → Cell Explorer
- Level 10 → Genetics Scholar
- Level 20 → Biology Master

---

## Achievement System

Students unlock badges for milestones.

Examples:
- 7-Day Study Streak
- Quiz Perfectionist
- Cell Biology Master
- Recovery Champion
- Diagram Expert

---

# UI Surfaces

Gamification must appear across multiple student interactions.

---

# UI Surface 1 — Student Dashboard

## Purpose
Primary student progression hub.

## Components

### XP Card
Displays:
- current XP,
- XP toward next level.

### Streak Widget
Displays:
- current streak,
- longest streak,
- streak status.

### Mastery Progress Bar
Displays:
- current level,
- level progress,
- mastery growth.

### Achievement Panel
Displays:
- unlocked badges,
- recent achievements,
- locked milestone previews.

### Recent Rewards Feed
Displays:
- recent XP gains,
- achievements,
- recovery progress rewards.

---

# UI Surface 2 — Quiz Completion Screen

## Purpose
High-impact reinforcement moment after assessments.

## Reward Modal Contents

Displays:
- XP earned,
- streak continuation,
- mastery increase,
- achievements unlocked,
- motivational feedback.

## Example UX

+120 XP
🔥 7-Day Biology Streak
🏆 Achievement Unlocked: Quiz Warrior
🧬 Cell Biology Mastery Increased

---

# UI Surface 3 — Tutoring Interface

## Purpose
Continuous micro-reinforcement during learning.

## Features

- XP rewards for Socratic sessions
- mastery notifications
- encouragement prompts
- hint efficiency bonuses

Example:
"Great reasoning! +15 XP"

---

# UI Surface 4 — Student Profile

## Purpose
Long-term learning identity and progression tracking.

## Components

- total XP,
- mastery history,
- achievement showcase,
- strongest subjects,
- learning statistics,
- streak history.

---

# UI Surface 5 — Recovery Plan Interface

## Purpose
Motivate struggling students through adaptive rewards.

## Features

- XP rewards for remediation tasks
- recovery milestone rewards
- weak-topic mastery tracking
- progress completion incentives

Example:
"Recovery Progress: 65% — Complete next quiz for +40 XP"

---

# User Stories

## GM-001 — XP Reward Engine

As a student,
I want to earn XP,
so that learning feels rewarding.

Acceptance Criteria:
- XP awarded after activities
- XP persisted in database
- XP visible across UI surfaces
- XP calculations deterministic

Priority: 1

---

## GM-002 — Daily Streak Tracking

As a student,
I want study streaks tracked,
so that I stay consistent.

Acceptance Criteria:
- Consecutive study days counted
- Missed days reset streak
- Current streak visible
- Longest streak stored

Priority: 1

---

## GM-003 — Mastery Level System

As a student,
I want mastery levels,
so that I can track biology growth.

Acceptance Criteria:
- Levels derived from XP
- Progress bar displayed
- Level-up events shown
- Level thresholds configurable

Priority: 1

---

## GM-004 — Achievement Badge System

As a student,
I want achievements,
so that milestones feel meaningful.

Acceptance Criteria:
- Badge unlock conditions configurable
- Badge persistence implemented
- Unlock notifications displayed
- Achievement panel functional

Priority: 2

---

## GM-005 — Quiz Reward Integration

As a student,
I want quizzes connected to rewards,
so that studying feels motivating.

Acceptance Criteria:
- Quiz completion grants XP
- Bonus XP for high scores
- Reward modal displayed
- Achievement checks triggered

Priority: 1

---

## GM-006 — Dashboard Gamification Widgets

As a student,
I want progression visible on my dashboard,
so that I stay motivated.

Acceptance Criteria:
- XP card implemented
- Streak widget implemented
- Mastery progress bar implemented
- Achievement panel implemented

Priority: 1

---

## GM-007 — Tutoring Reward Integration

As a student,
I want tutoring participation rewarded,
so that active learning feels engaging.

Acceptance Criteria:
- Tutoring sessions grant XP
- Feedback notifications displayed
- Reward triggers configurable

Priority: 2

---

## GM-008 — Recovery Plan Rewards

As a student,
I want recovery progress rewarded,
so that remediation feels motivating.

Acceptance Criteria:
- Recovery tasks grant XP
- Milestone rewards implemented
- Progress rewards displayed

Priority: 2

---

## GM-009 — Level-Up Notifications

As a student,
I want visible level-up feedback,
so that progression feels exciting.

Acceptance Criteria:
- Level-up modal implemented
- Animation supported
- Rewards displayed clearly

Priority: 3

---

# Ralph Loop Story Breakdown

## Pass 1 — Core Infrastructure
- XP database schema
- reward engine
- streak tracking
- basic APIs

---

## Pass 2 — Dashboard UI
- XP card
- streak widget
- mastery bar
- dashboard queries

---

## Pass 3 — Quiz Rewards
- reward modal
- quiz XP integration
- achievement checks

---

## Pass 4 — Achievement System
- badge models
- unlock logic
- achievement UI

---

## Pass 5 — Tutoring Integration
- tutoring XP
- contextual notifications
- hint efficiency rewards

---

## Pass 6 — Recovery Integration
- remediation rewards
- progress incentives
- mastery recalculation

---

# Database Requirements

## Table: student_gamification

Fields:
- user_id
- xp
- level
- current_streak
- longest_streak
- total_quizzes_completed
- total_study_sessions
- last_activity_date

---

## Table: achievements

Fields:
- id
- name
- description
- icon
- unlock_condition
- xp_reward

---

## Table: user_achievements

Fields:
- user_id
- achievement_id
- unlocked_at

---

## Table: reward_events

Fields:
- id
- user_id
- event_type
- xp_awarded
- metadata
- created_at

---

# API Requirements

## POST /gamification/reward

Purpose:
Award XP and update progression.

Input:
- userId
- eventType
- metadata

Output:
- xpAwarded
- level
- streak
- unlockedAchievements

---

## GET /gamification/profile

Returns:
- XP
- level
- streak
- achievements
- mastery progress

---

## GET /gamification/dashboard

Returns:
- dashboard widgets
- recent rewards
- progress stats

---

# Reward Rules

## Example XP Values

- Quiz completion → +50 XP
- Perfect quiz → +100 XP
- Daily streak continuation → +20 XP
- Socratic tutoring completion → +15 XP
- Recovery task completion → +40 XP
- Diagram labeling exercise → +30 XP

XP values should remain configurable.

---

# Design Constraints

## UI Principles

The system must:
- remain educational,
- avoid visual clutter,
- avoid manipulative dark patterns,
- support mobile responsiveness,
- remain accessible.

---

## Performance Constraints

- Reward updates must complete <500ms
- Dashboard loads must remain lightweight
- Reward calculations must be deterministic

---

# Analytics Requirements

Track:
- daily active learners,
- streak retention,
- XP distribution,
- achievement unlock frequency,
- recovery engagement,
- tutoring participation.

---

# Quality Checks

- XP calculation tests
- streak edge-case tests
- achievement unlock tests
- reward modal tests
- dashboard rendering tests
- mobile responsiveness tests
- accessibility checks

---

# Definition of Done

Feature is complete when:
- XP system operational
- streak tracking functional
- mastery levels implemented
- dashboard widgets operational
- quiz rewards integrated
- tutoring rewards integrated
- recovery rewards integrated
- achievements functional
- APIs stable
- tests passing
- documentation updated
