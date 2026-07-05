# Phase 1 — KML Foundation (Program A)

## Files to Create

### Group 1 — A1 Knowledge Registry (independent)
```
src/core/knowledge_registry/
  __init__.py              # exports KnowledgeRegistry
  models.py                # Pydantic models: KnowledgeObject, NewKnowledgeObject,
                           #   KnowledgeFilter, LifecycleState, LifecycleTransition
  service.py               # KnowledgeRegistry class with 8 methods
  events.py                # KnowledgeEvent Pydantic models emitted as side-effects

src/database/models.py     # ADD: KnowledgeObject SQLAlchemy model
                           #   (extends existing models.py, don't touch legacy models)
src/api/knowledge.py       # NEW: REST router wrapping KnowledgeRegistry
```

### Group 2 — A3 Storage Platform (independent)
```
src/core/storage/
  __init__.py              # exports StorageAdapter
  interface.py             # StorageAdapter ABC: store(), retrieve(), delete()
  local.py                 # LocalFileStorage implementation
```

### Group 3 — A4 Event Infrastructure (independent)
```
src/core/event_infrastructure/
  __init__.py              # exports RedisStreamProducer, RedisStreamConsumer
  producer.py              # RedisStreamProducer: push to knowledge:processing stream
  consumer.py              # RedisStreamConsumer ABC + base worker class
```

### Group 4 — A2 Workspace Service (depends on A1 models for FK)
```
src/core/workspace/
  __init__.py              # exports WorkspaceService
  models.py                # Pydantic models: Workspace, WorkspaceMember, WorkspaceRole
  service.py               # WorkspaceService: CRUD, membership, ClassGroup seeding

src/database/models.py     # ADD: Workspace SQLAlchemy model (class_group_id FK)
                           #   workspace_members association table
```

## Order
1. Group 1 (A1) — parallel with Group 2 (A3) and Group 3 (A4)
2. Group 4 (A2) — after A1 models exist (needs KnowledgeObject FK)
