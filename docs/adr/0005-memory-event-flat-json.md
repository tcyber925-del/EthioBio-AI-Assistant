# Memory Event Storage — Flat JSONB Over Normalized Schema

The PRD-001 specification described separate `memory_event_metadata` and `memory_event_link` tables. We chose to keep the existing flat JSON `event_metadata` column on `memory_events` instead.

Context: Event metadata is inherently heterogeneous — `assessment_completed` has different fields than `intervention_launched`. Normalizing would require either one table per event type or an EAV anti-pattern. PostgreSQL JSONB provides queryable metadata via `@>` and `->>` operators with GIN index support, which is sufficient for all current and foreseeable query patterns.

**Status:** accepted

**Consequences:** Future consumers query memory events via JSONB operators. If event-to-entity links (e.g., "this assessment event references this recovery plan") become a first-class query pattern, a lightweight `memory_event_links(event_id, entity_type, entity_id)` table can be added as an opt-in extension — no migration to the event table itself.
