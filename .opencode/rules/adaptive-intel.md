# Adaptive Quiz & Recommendation Engine

Read when: working on adaptive quiz, question attempts, student ability, or learning recommendations.

## Adaptive Quiz Engine (`src/agents/adaptive_quiz.py`, `src/database/models.py`)

Bayesian IRT model tracking per-topic student ability.

### Models

- `QuestionAttempt` (id, user_id, question_id, quiz_id, correct, time_spent, hints_used, attempt_number)
- `StudentAbility` (user_id + topic composite PK, ability_score, uncertainty, attempt_count)
- `Question.difficulty_score` — Float column (-1.0 easy, 0.0 medium, 1.0 hard)

### Functions (in `src/agents/adaptive_quiz.py`)

- `record_attempt()` — records attempt with auto-incrementing attempt_number
- `estimate_bayesian_ability()` — logit-based Bayesian estimation with prior weighting
- `update_ability()` — upserts per-topic ability after quiz submit
- `get_ability()` — returns (ability_score, uncertainty, attempt_count)
- `select_adaptive_questions()` — selects closest to `ability + 0.5` (optimal challenge)
- `migrate_difficulty_scores()` — one-time string-to-numeric migration

### Usage

- **Adaptive quiz**: Pass `"adaptive": true` in `POST /quiz/generate`.
- **Wiring**: `POST /quiz/submit` auto-records attempts and updates ability.
- **Requires user_id**: `select_adaptive_questions()` falls back to random without user_id.

## Learning Recommendation Engine (`src/core/learning_intelligence/recommendation/`)

Prioritized educational actions from `LearnerSnapshot` data.

### Models (`recommendation/models/`)

- `LearningActionType` enum (9 values)
- `LearningRecommendation` pydantic model (id, action_type, topic, priority_score, reason, explanation, generated_at, metadata)

### Scoring (`recommendation/scoring/`)

- `PriorityCalculator`: `RAW_WEIGHTS`, `MAX_POSSIBLE_SCORE = 120`, `normalize()` (÷120, clamp 0-1), `deduplicate()` (merge by action_type+topic, keep higher score), `score_and_sort()` (normalize → dedup → sort desc → top 5)

### Rules (`recommendation/rules/`)

5 async generators: `mastery_rules`, `recovery_rules`, `review_rules`, `misconception_rules`, `engagement_rules` — each `(snapshot: LearnerSnapshot) -> list[LearningRecommendation]`

### Services (`recommendation/services/`)

- `RecommendationEngine`: parallel gather → score_and_sort → ID assignment
- `RecommendationService`: cache-first facade (CacheManager, prefix `recommendations:`)

### API (`src/api/intelligence/router.py`)

- `GET /intelligence/recommendations/{user_id}` (top 5)
- `GET /intelligence/next-action/{user_id}` (single best or `{}`)

### Package Convention

Each sub-package (`models/`, `scoring/`, `rules/`, `services/`) has its own `__init__.py` re-exporting the public API.

### Tests

- `tests/test_priority_calculator.py`
- `tests/test_recommendation_rules.py`
- `tests/test_recommendation_engine.py`
- `tests/test_recommendation_service.py`
