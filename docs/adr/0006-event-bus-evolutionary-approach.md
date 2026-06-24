# Event Bus — Evolutionary Approach Over PRD-002 Specification

PRD-002 described a full event-driven architecture with publisher, PostgreSQL-backed broker, subscriber system, event registry, and replay infrastructure. We chose to evolve the existing `EventLogger` with schema validation and an in-process subscriber registry instead.

Context: The current codebase is a single deployed service (monolith). All event consumers (UEML, Learning Intelligence, Knowledge Graph, Teacher Copilot) live in the same process. A dedicated broker/queue/replay layer would be premature abstraction. The existing `MemoryEvent` table already serves as an append-only event store queryable via JSONB operators. The `EventLogger` class already provides a single entry point for event creation. What's missing is schema validation (all events must conform to the standard `EducationalEvent` interface) and a lightweight subscriber pattern — in-process callbacks, not a message broker.

**Status:** accepted

**Consequences:** The formal Event Bus with Redis Streams or Kafka is deferred until multiple independent services or processes require decoupling. The `EventLogger` has been extended with: event schema validation (8 known event types in `SCHEMA_REGISTRY` at `src/core/memory/event_logger.py` — see ADR-0009), and a `SubscriberRegistry` that dispatches events to registered callbacks within the same process. This covers all current consumers while adding <200 lines of code instead of a new infrastructure layer.
