# Knowledge Graph — Named Adjacency Tables Over Graph Abstraction Layer

PRD-003 specified PostgreSQL + a generic Graph Abstraction Layer with node/edge tables, a graph query engine, and a graph reasoning engine. We chose named adjacency tables with recursive CTEs instead.

Context: The existing codebase already encodes many relationships in domain-specific tables (StudentMastery, MisconceptionPattern, StudentAbility, TopicMasteryHistory). What's missing is explicit relationship tables for prerequisite chains, misconception→topic mappings, and intervention→outcome links. A generic Graph Abstraction Layer (node/edge store) would add infrastructure complexity without matching the well-known, stable set of relationship types the platform actually needs. Recursive CTEs in PostgreSQL handle prerequisite chain traversal efficiently for the expected data volumes (<1000 topics, <10000 students per school).

**Status:** accepted

**Considered Options:**
1. **Generic node/edge tables + Graph Abstraction Layer** — Matches the PRD but adds infrastructure before query patterns validate the need. Harder to understand for new developers.
2. **Named adjacency tables with recursive CTEs** — Self-documenting (each table name describes the relationship), performant for known patterns, no new infrastructure. Chosen.
3. **Extend existing domain models only** — No new tables, encode relationships in existing models. Rejected because prerequisite chains and intervention outcomes need dedicated storage.

**Consequences:** The `src/core/knowledge_graph/builder/` creates records in named adjacency tables rather than generic nodes/edges. Graph queries use recursive CTEs and joins instead of a graph query language. If query patterns emerge that recursive CTEs cannot handle efficiently (e.g., multi-hop graph traversal across many relationship types), a dedicated graph engine can be introduced under the existing builder/reasoning/query interfaces — the named tables become the source of truth that populates the graph engine.
