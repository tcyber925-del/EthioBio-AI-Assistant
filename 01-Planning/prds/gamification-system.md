# Feature PRD — Gamification System

## Project
EthioBio AI Assistant

## Branch
feature/gamification-system

---

# Overview

Implement a gamified biology learning experience using:
- XP,
- mastery levels,
- streaks,
- achievements,
- progress tracking.

The system should increase:
- motivation,
- retention,
- study consistency,
- engagement.

---

# Goals

- Encourage daily study habits
- Increase quiz completion
- Reward progress
- Improve long-term engagement

---

# Non-Goals

- Competitive multiplayer
- Real-money rewards
- Public leaderboards
- Social features

---

# Core Mechanics

## XP
Awarded for:
- quizzes,
- correct answers,
- streak completion,
- recovery plan completion.

## Streaks
Tracks consecutive study days.

## Mastery Levels
Represents biology competency progression.

## Achievements
Badges for milestones.

---

# User Stories

## GM-001 — XP Reward Engine

As a student,
I want to earn XP,
so that progress feels rewarding.

Acceptance Criteria:
- XP awarded after activities
- XP persisted in database
- XP visible in profile UI

Priority: 1

---

## GM-002 — Daily Streak Tracking

As a student,
I want study streaks tracked,
so that I stay consistent.

Acceptance Criteria:
- Consecutive days counted
- Missed day resets streak
- Current streak visible

Priority: 1

---

## GM-003 — Mastery Level System

As a student,
I want mastery levels,
so that I can track biology growth.

Acceptance Criteria:
- Levels calculated from XP
- Progress bar displayed
- Level-up notifications shown

Priority: 2

---

## GM-004 — Achievement Badges

As a student,
I want achievement badges,
so that milestones feel meaningful.

Acceptance Criteria:
- Badge conditions configurable
- Badge UI exists
- Earned badges persisted

Priority: 2

---

## GM-005 — Quiz Reward Integration

As a student,
I want quizzes connected to rewards,
so that studying feels motivating.

Acceptance Criteria:
- Quiz completion awards XP
- Bonus XP for high scores
- Rewards displayed after completion

Priority: 1

---

# Database Requirements

## Tables

### student_gamification
- user_id
- xp
- level
- streak
- longest_streak

### achievements
- id
- name
- description
- icon

### user_achievements
- user_id
- achievement_id
- unlocked_at

---

# API Requirements

## POST /gamification/reward
Awards XP and updates streaks.

## GET /gamification/profile
Returns:
- XP
- level
- streak
- achievements

---

# Quality Checks

- XP calculation tests
- Streak edge-case tests
- Achievement unlock tests
- UI rendering tests

---

# Definition of Done

- XP system operational
- Streak system operational
- Levels functional
- Achievements functional
- Quiz integration complete
- Tests passing