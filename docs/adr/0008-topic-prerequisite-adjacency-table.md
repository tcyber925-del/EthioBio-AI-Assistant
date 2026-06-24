# Topic-Prequisite Adjacency Tables for Educational Knowledge Graph

The Educational Knowledge Graph Strategy (ADR-0007) specified named adjacency tables for each relationship type rather than a generic node/edge store. We chose `topic_prerequisites` as the first adjacency table, powered by `WITH RECURSIVE` CTEs for chain traversal.

**Status:** accepted

## Context

PRD-003 describes prerequisite discovery, curriculum sequencing, and gap analysis using a Knowledge Graph. The question was which approach to take: a generic graph abstraction layer (triple store) or directly named tables.

## Decision

Named adjacency table `topic_prerequisites` with columns `topic_id`, `prerequisite_topic_id`, `relationship_type`, `grade_level`. Two recursive CTEs (`prerequisite_chain` and `dependent_chain`) traverse the graph. A third query (`gap_analysis`) intersects the prerequisite chain with `student_mastery.average_score` to find unmastered prerequisites.

The `RelationshipBuilder` in `src/core/knowledge_graph/builder/` manages CRUD. The `GraphReasoningEngine` in `src/core/knowledge_graph/engine.py` executes the CTEs.

## Consequences

- Adding a new relationship type (e.g., `is_remediation_for`, `belongs_to_unit`) means adding a new adjacency table, not extending the existing one. This keeps each table's query pattern simple and indexable.
- Recursive CTEs with cycle detection handle the primary traversal patterns. Deep traversals (depth > 5) are explicitly bounded by a `max_depth` parameter.
- Gap analysis requires the prerequisite chain to intersect with `student_mastery`, which joins two systems (KG + mastery tracking). This is a simple PK join on topic name, but will need to be updated if topic identifiers become non-textual.
- Future relationship tables should follow the same pattern: source_id, target_id, relationship_type (string enum), and any relationship-specific metadata columns. The `RelationshipBuilder` and `GraphReasoningEngine` can be extended with per-table methods.
