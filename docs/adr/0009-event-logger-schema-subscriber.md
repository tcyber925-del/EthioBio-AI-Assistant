# EventLogger Schema Validation and Subscriber Registry

The EventLogger at `src/core/memory/event_logger.py` was evolved with schema validation for event metadata and an in-process subscriber registry. This is the concrete implementation of the Event Bus Strategy (PRD-002 / ADR-0006), which deferred a full event-driven architecture in favor of evolving the existing logger.

**Status:** accepted

## Context

PRD-002 described a full Event Bus with publisher/broker/subscriber/registry/replay capabilities. The existing `EventLogger` was a simple `db.add(MemoryEvent(...))` wrapper with no validation and no notification mechanism. Multiple downstream features (gamification, recommendations, notifications) need to react to events without tight coupling.

## Decision

Two additions to the existing `EventLogger`:

1. **Schema Registry** (`SCHEMA_REGISTRY`): A dict of `EventSchema` objects keyed by event type. 8 event types are registered: `session_started`, `quiz_completed`, `lesson_viewed`, `recovery_task_done`, `misconception_detected`, `xp_awarded`, `streak_updated`, `achievement_unlocked`. Each schema defines required fields, optional fields, and typed metadata validation. Unknown event types are accepted with a warning — the registry is additive, not restrictive.

2. **Subscriber Registry**: An in-process `dict[str, list[Callable]]` keyed by event type. Handlers register via `subscribe(event_type, handler)` or `subscribe_all(handler)`. On each `log()`, subscribers are notified asynchronously with `(event_type, user_id, metadata, event_id)`. Both sync and async handlers are supported via inspection with `hasattr(result, '__await__')`. Errors in one subscriber don't affect others.

## Consequences

- Schema validation catches malformed event data at the logging boundary, before it reaches the database. This prevents garbage-in-garbage-out for downstream consumers.
- The subscriber registry enables decoupled reactions: gamification can subscribe to `xp_awarded`, recommendations to `quiz_completed`, etc., without the `EventLogger` knowing about them.
- This is explicitly a monolith-scale solution. No external broker, no persistence, no replay. When the platform decomposes into multiple services, the subscriber registry becomes a message producer to a proper event bus (Redis Streams → Kafka).
- New event types can be added by defining a schema and registering handlers. No code changes to the logger itself.
- Schema validation errors raise `EventValidationError`, which propagates to the caller. This is intentional — callers must decide whether an invalid event should fail the operation or be silently dropped.
