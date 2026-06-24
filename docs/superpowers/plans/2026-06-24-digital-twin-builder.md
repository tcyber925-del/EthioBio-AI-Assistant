# Digital Twin Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Twin Builder sub-project 1 of PRD-009 — materialized `student_digital_twins` table, event-driven builder service, GET/POST API, and dashboard twin viewer.

**Architecture:** Event bus → TwinBuilder.rebuild(user_id) → gather 6 dimensions from source tables → upsert student_digital_twins → emit twin_updated. Full rebuild per trigger.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy async, PostgreSQL JSONB, Next.js 14 App Router

---

### Task 1: Data Model + Schema

**Files:**
- Modify: `src/database/models.py` (add `StudentDigitalTwin`)
- Create: `src/schemas/digital_twin.py`

- [ ] **Step 1: Add `StudentDigitalTwin` model to models.py**

After the last existing model (before the file end), add:

```python
class StudentDigitalTwin(Base):
    __tablename__ = "student_digital_twins"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    knowledge_state: Mapped[dict] = mapped_column(JSON, default=dict)
    mastery_state: Mapped[dict] = mapped_column(JSON, default=dict)
    misconception_state: Mapped[dict] = mapped_column(JSON, default=dict)
    retention_state: Mapped[dict] = mapped_column(JSON, default=dict)
    readiness_state: Mapped[dict] = mapped_column(JSON, default=dict)
    intervention_state: Mapped[dict] = mapped_column(JSON, default=dict)
    overall_health: Mapped[str] = mapped_column(String(20), default="unknown")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    last_built_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(backref="digital_twin", uselist=False)
```

- [ ] **Step 2: Write the failing test for the model**

```python
# tests/test_digital_twin.py
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import StudentDigitalTwin


class TestStudentDigitalTwinModel:
    async def test_create_twin(self, db_session: AsyncSession):
        user_id = uuid.uuid4()
        twin = StudentDigitalTwin(
            user_id=user_id,
            knowledge_state={"overall": 0.75, "topics": {}},
            mastery_state={"overall": 0.8, "topics": {}},
            overall_health="healthy",
            confidence=0.9,
        )
        db_session.add(twin)
        await db_session.commit()
        await db_session.refresh(twin)

        assert twin.user_id == user_id
        assert twin.knowledge_state["overall"] == 0.75
        assert twin.overall_health == "healthy"
        assert twin.confidence == 0.9
        assert isinstance(twin.created_at, datetime)

    async def test_twin_defaults(self, db_session: AsyncSession):
        user_id = uuid.uuid4()
        twin = StudentDigitalTwin(user_id=user_id)
        db_session.add(twin)
        await db_session.commit()
        await db_session.refresh(twin)

        assert twin.overall_health == "unknown"
        assert twin.confidence == 0.0
        assert twin.knowledge_state == {}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_digital_twin.py::TestStudentDigitalTwinModel -v`
Expected: FAIL — `StudentDigitalTwin` not defined yet

- [ ] **Step 4: Add the model code**

Add the `StudentDigitalTwin` class to `src/database/models.py` (after `LessonPlan` class, before `Question`). Insert after line 188 (after `used_in_class` / `updated_at` lines).

- [ ] **Step 5: Create schemas file**

```python
# src/schemas/digital_twin.py
from typing import Optional
from uuid import UUID

from src.schemas.base import SchemaModel


class DigitalTwinResponse(SchemaModel):
    user_id: UUID
    knowledge_state: dict = {}
    mastery_state: dict = {}
    misconception_state: dict = {}
    retention_state: dict = {}
    readiness_state: dict = {}
    intervention_state: dict = {}
    overall_health: str = "unknown"
    confidence: float = 0.0
    last_built_at: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


class DigitalTwinDashboardResponse(SchemaModel):
    user_id: UUID
    overall_health: str = "unknown"
    dimension_summary: dict = {}
    risk_indicators: list[dict] = []
    last_built_at: Optional[str] = None
```

- [ ] **Step 6: Run tests to verify model passes**

Run: `pytest tests/test_digital_twin.py::TestStudentDigitalTwinModel -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/database/models.py src/schemas/digital_twin.py tests/test_digital_twin.py
git commit -m "feat: add StudentDigitalTwin model and schemas"
```

---

### Task 2: Twin Builder Service

**Files:**
- Create: `src/core/digital_twin/__init__.py`
- Create: `src/core/digital_twin/builder.py`
- Test: `tests/test_digital_twin.py`

- [ ] **Step 1: Create package init**

```python
# src/core/digital_twin/__init__.py
from src.core.digital_twin.builder import TwinBuilder

__all__ = ["TwinBuilder"]
```

- [ ] **Step 2: Write failing test for gather_knowledge_state**

```python
# tests/test_digital_twin.py (append)
import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.digital_twin.builder import TwinBuilder
from src.database.models import StudentAbility


class TestTwinBuilder:
    async def test_gather_knowledge_state(self, db_session: AsyncSession):
        user_id = uuid.uuid4()
        db_session.add(StudentAbility(
            user_id=user_id, topic="Cell Division",
            ability_score=0.72, uncertainty=0.3, attempt_count=8,
        ))
        db_session.add(StudentAbility(
            user_id=user_id, topic="Genetics",
            ability_score=0.88, uncertainty=0.2, attempt_count=12,
        ))
        await db_session.commit()

        builder = TwinBuilder(db_session)
        result = await builder.gather_knowledge_state(user_id)

        assert "overall" in result
        assert "topics" in result
        assert result["topics"]["Cell Division"]["score"] == 0.72
        assert result["topics"]["Genetics"]["score"] == 0.88
        assert result["topics"]["Cell Division"]["data_points"] == 8

    async def test_gather_knowledge_state_empty(self, db_session: AsyncSession):
        builder = TwinBuilder(db_session)
        result = await builder.gather_knowledge_state(uuid.uuid4())
        assert result == {}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_digital_twin.py::TestTwinBuilder -v`
Expected: FAIL — `TwinBuilder` not defined

- [ ] **Step 4: Write the builder service**

```python
# src/core/digital_twin/builder.py
from uuid import UUID

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    InterventionAssignment,
    MisconceptionPattern,
    SpacedRepetitionSchedule,
    StudentAbility,
    StudentDigitalTwin,
    StudentMastery,
    TopicPrerequisite,
)

logger = structlog.get_logger()


class TwinBuilder:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def gather_knowledge_state(self, user_id: UUID) -> dict:
        result = await self.session.execute(
            select(StudentAbility).where(
                StudentAbility.user_id == user_id,
                StudentAbility.ability_score != 0.0,
            )
        )
        rows = result.scalars().all()
        if not rows:
            return {}

        topics = {}
        total = 0.0
        for row in rows:
            topics[row.topic] = {
                "score": round(row.ability_score, 2),
                "uncertainty": round(row.uncertainty, 2),
                "data_points": row.attempt_count,
                "last_updated": (
                    row.updated_at.isoformat() if row.updated_at else None
                ),
                "confidence": round(
                    min(row.attempt_count / 10, 1.0) * 0.5
                    + 0.5 * max(0, 1 - (row.uncertainty / 5)), 2
                ),
            }
            total += row.ability_score

        return {"overall": round(total / len(rows), 2), "topics": topics}

    async def gather_mastery_state(self, user_id: UUID) -> dict:
        result = await self.session.execute(
            select(StudentMastery).where(StudentMastery.user_id == user_id)
        )
        rows = result.scalars().all()
        if not rows:
            return {}

        topics = {}
        total = 0.0
        for row in rows:
            topics[row.topic] = {
                "mastery_score": row.average_score,
                "level": row.severity,
                "data_points": row.attempt_count,
                "last_assessed": (
                    row.last_assessed_at.isoformat()
                    if row.last_assessed_at else None
                ),
            }
            total += row.average_score

        return {"overall": round(total / len(rows), 2), "topics": topics}

    async def gather_misconception_state(self, user_id: UUID) -> dict:
        result = await self.session.execute(
            select(MisconceptionPattern).where(
                MisconceptionPattern.user_id == user_id,
            )
        )
        rows = result.scalars().all()
        active = [r for r in rows if not r.resolved]
        resolved = [r for r in rows if r.resolved]

        topics = {}
        for row in active:
            topic = row.topic
            if topic not in topics:
                topics[topic] = []
            topics[topic].append({
                "pattern": row.pattern_description,
                "severity": row.severity,
                "frequency": row.frequency,
                "active_since": (
                    row.first_detected_at.isoformat()
                    if row.first_detected_at else None
                ),
            })

        return {
            "total_active": len(active),
            "total_resolved": len(resolved),
            "topics": topics,
        }

    async def gather_retention_state(self, user_id: UUID) -> dict:
        result = await self.session.execute(
            select(SpacedRepetitionSchedule).where(
                SpacedRepetitionSchedule.user_id == user_id,
            )
        )
        rows = result.scalars().all()
        if not rows:
            return {}

        topics = {}
        total = 0.0
        now = func.now()
        for row in rows:
            days_since = None
            forgetting_risk = "unknown"
            if row.last_reviewed_at:
                delta = await self.session.execute(
                    select(func.extract(
                        "epoch", now - row.last_reviewed_at
                    ) / 86400)
                )
                days_since = round(delta.scalar() or 0)
                if days_since > 14:
                    forgetting_risk = "high"
                elif days_since > 7:
                    forgetting_risk = "medium"
                else:
                    forgetting_risk = "low"

            topics[row.topic] = {
                "retention_score": row.mastery_score,
                "last_reviewed": (
                    row.last_reviewed_at.isoformat()
                    if row.last_reviewed_at else None
                ),
                "days_since_review": days_since,
                "forgetting_risk": forgetting_risk,
                "next_review": (
                    row.next_review_at.isoformat()
                    if row.next_review_at else None
                ),
            }
            total += row.mastery_score

        return {"overall": round(total / len(rows), 2), "topics": topics}

    async def gather_readiness_state(self, user_id: UUID) -> dict:
        result = await self.session.execute(
            select(StudentMastery).where(
                StudentMastery.user_id == user_id,
            )
        )
        rows = result.scalars().all()
        if not rows:
            return {}

        topics = {}
        total = 0.0
        for row in rows:
            prereq_result = await self.session.execute(
                select(TopicPrerequisite).where(
                    TopicPrerequisite.topic_id.in_(
                        select(TopicPrerequisite.prerequisite_topic_id).where(
                            TopicPrerequisite.topic_id.in_(
                                select(func.identity(row.topic))
                            )
                        )
                    )
                )
            )
            prereqs_met = prereq_result.scalar_one_or_none() is None

            risk = "low"
            if row.average_score < 0.4:
                risk = "high"
            elif row.average_score < 0.6:
                risk = "medium"

            topics[row.topic] = {
                "readiness_score": row.average_score,
                "prerequisites_met": prereqs_met,
                "risk_level": risk,
            }
            total += row.average_score

        return {"overall": round(total / len(rows), 2), "topics": topics}

    async def gather_intervention_state(self, user_id: UUID) -> dict:
        result = await self.session.execute(
            select(InterventionAssignment).where(
                InterventionAssignment.user_id == user_id,
            )
        )
        rows = result.scalars().all()

        active = [r for r in rows if r.status == "active"]
        completed = [r for r in rows if r.status == "completed"]
        by_type: dict = {}
        for row in rows:
            t = row.intervention_type
            if t not in by_type:
                by_type[t] = {"assigned": 0, "completed": 0, "avg_effectiveness": 0.0}
            by_type[t]["assigned"] += 1
            if row.status == "completed" and row.effectiveness_score is not None:
                c = by_type[t]
                old_total = c["avg_effectiveness"] * c["completed"]
                c["completed"] += 1
                c["avg_effectiveness"] = round(
                    (old_total + row.effectiveness_score) / c["completed"], 2
                )

        effectiveness_scores = [
            r.effectiveness_score for r in completed
            if r.effectiveness_score is not None
        ]
        responsiveness = (
            round(sum(effectiveness_scores) / len(effectiveness_scores), 2)
            if effectiveness_scores else 0.0
        )

        return {
            "active_count": len(active),
            "completed_count": len(completed),
            "responsiveness": responsiveness,
            "by_type": by_type,
        }

    async def rebuild(self, user_id: UUID) -> dict:
        state = {
            "knowledge_state": await self.gather_knowledge_state(user_id),
            "mastery_state": await self.gather_mastery_state(user_id),
            "misconception_state": await self.gather_misconception_state(user_id),
            "retention_state": await self.gather_retention_state(user_id),
            "readiness_state": await self.gather_readiness_state(user_id),
            "intervention_state": await self.gather_intervention_state(user_id),
        }
        state["overall_health"] = self._compute_health(state)
        state["confidence"] = self._compute_confidence(state)

        existing = await self.session.get(StudentDigitalTwin, user_id)
        if existing:
            for key, val in state.items():
                setattr(existing, key, val)
            existing.last_built_at = func.now()
        else:
            self.session.add(StudentDigitalTwin(
                user_id=user_id, **state, last_built_at=func.now(),
            ))
        await self.session.commit()
        return state

    def _compute_health(self, state: dict) -> str:
        scores = []
        if "knowledge_state" in state and state["knowledge_state"]:
            scores.append(state["knowledge_state"].get("overall", 0))
        if "mastery_state" in state and state["mastery_state"]:
            scores.append(state["mastery_state"].get("overall", 0))
        if "retention_state" in state and state["retention_state"]:
            scores.append(state["retention_state"].get("overall", 0))
        if "readiness_state" in state and state["readiness_state"]:
            scores.append(state["readiness_state"].get("overall", 0))
        if not scores:
            return "unknown"
        avg = sum(scores) / len(scores)
        if avg >= 0.7:
            return "healthy"
        if avg >= 0.4:
            return "needs_attention"
        return "at_risk"

    def _compute_confidence(self, state: dict) -> float:
        dimensions = [
            "knowledge_state", "mastery_state", "misconception_state",
            "retention_state", "readiness_state", "intervention_state",
        ]
        scores = []
        for dim in dimensions:
            val = state.get(dim, {})
            if not val:
                continue
            if dim == "misconception_state":
                data_points = val.get("total_active", 0) + val.get("total_resolved", 0)
            elif dim == "intervention_state":
                data_points = val.get("active_count", 0) + val.get("completed_count", 0)
            else:
                topics = val.get("topics", {})
                if not topics:
                    continue
                data_points = sum(
                    t.get("data_points", 0) for t in topics.values()
                    if isinstance(t, dict)
                )
            freshness = 0.5  # simplified — full decay in future sub-project
            volume = min(data_points / 10, 1.0)
            scores.append((0.5 * freshness) + (0.5 * volume))
        return round(sum(scores) / len(scores), 2) if scores else 0.0
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_digital_twin.py::TestTwinBuilder -v`
Expected: PASS

- [ ] **Step 6: Add rebuild integration test**

```python
# tests/test_digital_twin.py (append)
class TestTwinBuilderRebuild:
    async def test_rebuild_creates_twin(self, db_session: AsyncSession):
        user_id = uuid.uuid4()
        db_session.add(StudentAbility(
            user_id=user_id, topic="Cell Division",
            ability_score=0.72, uncertainty=0.3, attempt_count=8,
        ))
        await db_session.commit()

        builder = TwinBuilder(db_session)
        state = await builder.rebuild(user_id)

        assert "knowledge_state" in state
        assert state["overall_health"] in ("healthy", "needs_attention", "unknown")
        assert state["confidence"] >= 0.0

        twin = await db_session.get(StudentDigitalTwin, user_id)
        assert twin is not None
        assert twin.knowledge_state["topics"]["Cell Division"]["score"] == 0.72

    async def test_rebuild_updates_existing(self, db_session: AsyncSession):
        user_id = uuid.uuid4()
        db_session.add(StudentDigitalTwin(
            user_id=user_id, overall_health="unknown", confidence=0.0,
        ))
        db_session.add(StudentAbility(
            user_id=user_id, topic="Genetics",
            ability_score=0.9, uncertainty=0.1, attempt_count=15,
        ))
        await db_session.commit()

        builder = TwinBuilder(db_session)
        state = await builder.rebuild(user_id)

        twin = await db_session.get(StudentDigitalTwin, user_id)
        assert twin.knowledge_state["topics"]["Genetics"]["score"] == 0.9
        assert twin.overall_health != "unknown" or state["overall_health"] != "unknown"
```

- [ ] **Step 7: Run rebuild tests**

Run: `pytest tests/test_digital_twin.py::TestTwinBuilderRebuild -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/core/digital_twin/ tests/test_digital_twin.py
git commit -m "feat: add TwinBuilder service with 6 dimension gatherers"
```

---

### Task 3: Event Subscription

**Files:**
- Create: `src/core/digital_twin/events.py`
- Test (optional): Can be tested via integration with event bus

- [ ] **Step 1: Create event subscriber**

```python
# src/core/digital_twin/events.py
import structlog
from uuid import UUID

from src.core.digital_twin.builder import TwinBuilder
from src.core.memory.event_logger import EventLogger

logger = structlog.get_logger()

TWIN_EVENT_TYPES = [
    "assessment_completed",
    "lesson_delivered",
    "intervention_completed",
    "intervention_assigned",
    "misconception_detected",
    "misconception_resolved",
]


async def twin_event_handler(
    event_type: str,
    user_id: UUID,
    metadata: dict | None = None,
    **kwargs,
):
    if event_type not in TWIN_EVENT_TYPES:
        return
    from src.database.session import async_session_factory
    async with async_session_factory() as session:
        try:
            builder = TwinBuilder(session)
            state = await builder.rebuild(user_id)
            logger.info(
                "twin_rebuilt",
                user_id=str(user_id),
                event_type=event_type,
                health=state.get("overall_health"),
            )
        except Exception:
            logger.exception(
                "twin_rebuild_failed",
                user_id=str(user_id),
                event_type=event_type,
            )


def register_twin_subscribers(event_logger: EventLogger):
    for event_type in TWIN_EVENT_TYPES:
        event_logger.subscribe(event_type, twin_event_handler)
    logger.info("twin_subscribers_registered", count=len(TWIN_EVENT_TYPES))
```

- [ ] **Step 2: Wire subscriber registration into app startup**

Add to `src/main.py` after router registrations (around line 145):

```python
from src.core.digital_twin.events import register_twin_subscribers
from src.core.memory.event_logger import event_logger

register_twin_subscribers(event_logger)
```

- [ ] **Step 3: Commit**

```bash
git add src/core/digital_twin/events.py src/main.py
git commit -m "feat: add event-driven twin rebuild subscriber"
```

---

### Task 4: API Endpoints

**Files:**
- Create: `src/api/digital_twin.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_digital_twin.py (append)
class TestDigitalTwinAPI:
    async def test_get_twin_404(self, async_client):
        response = await async_client.get(
            f"/digital-twin/{uuid.uuid4()}"
        )
        assert response.status_code == 404

    async def test_get_twin_success(self, async_client, db_session):
        user_id = uuid.uuid4()
        db_session.add(StudentDigitalTwin(
            user_id=user_id, overall_health="healthy",
            confidence=0.85,
        ))
        await db_session.commit()

        response = await async_client.get(f"/digital-twin/{user_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["overall_health"] == "healthy"
        assert data["confidence"] == 0.85

    async def test_rebuild_twin(self, async_client, db_session):
        user_id = uuid.uuid4()
        db_session.add(StudentAbility(
            user_id=user_id, topic="Test Topic",
            ability_score=0.8, uncertainty=0.2, attempt_count=5,
        ))
        await db_session.commit()

        response = await async_client.post(
            f"/digital-twin/{user_id}/rebuild"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["knowledge_state"]["topics"]["Test Topic"]["score"] == 0.8

    async def test_get_dashboard(self, async_client, db_session):
        user_id = uuid.uuid4()
        db_session.add(StudentDigitalTwin(
            user_id=user_id, overall_health="needs_attention",
            confidence=0.7,
            knowledge_state={"overall": 0.65, "topics": {}},
            mastery_state={"overall": 0.7, "topics": {}},
        ))
        await db_session.commit()

        response = await async_client.get(
            f"/digital-twin/{user_id}/dashboard"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["overall_health"] == "needs_attention"
        assert "dimension_summary" in data
        assert "risk_indicators" in data
```

- [ ] **Step 2: Run API tests (expect fail)**

Run: `pytest tests/test_digital_twin.py::TestDigitalTwinAPI -v`
Expected: FAIL — endpoint not defined

- [ ] **Step 3: Write the API endpoints**

```python
# src/api/digital_twin.py
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.digital_twin import TwinBuilder
from src.database.models import StudentDigitalTwin
from src.database.session import get_session
from src.schemas.digital_twin import DigitalTwinDashboardResponse, DigitalTwinResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/digital-twin", tags=["Digital Twin"])


@router.get("/{user_id}", response_model=DigitalTwinResponse)
async def get_twin(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    twin = await session.get(StudentDigitalTwin, user_id)
    if not twin:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    return _twin_to_response(twin)


@router.post("/{user_id}/rebuild", response_model=DigitalTwinResponse)
async def rebuild_twin(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    builder = TwinBuilder(session)
    try:
        state = await builder.rebuild(user_id)
    except Exception as e:
        logger.error("twin_rebuild_error", user_id=str(user_id), error=str(e))
        raise HTTPException(status_code=500, detail=f"Rebuild failed: {e}")

    twin = await session.get(StudentDigitalTwin, user_id)
    if not twin:
        raise HTTPException(status_code=500, detail="Twin not found after rebuild")
    return _twin_to_response(twin)


@router.get("/{user_id}/dashboard", response_model=DigitalTwinDashboardResponse)
async def get_twin_dashboard(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    twin = await session.get(StudentDigitalTwin, user_id)
    if not twin:
        raise HTTPException(status_code=404, detail="Digital twin not found")

    dims = {
        "knowledge": twin.knowledge_state,
        "mastery": twin.mastery_state,
        "misconceptions": twin.misconception_state,
        "retention": twin.retention_state,
        "readiness": twin.readiness_state,
        "interventions": twin.intervention_state,
    }
    summary = {}
    for name, val in dims.items():
        if val and isinstance(val, dict):
            if name == "misconceptions":
                summary[name] = {
                    "active": val.get("total_active", 0),
                    "resolved": val.get("total_resolved", 0),
                }
            elif name == "interventions":
                summary[name] = {
                    "active": val.get("active_count", 0),
                    "completed": val.get("completed_count", 0),
                }
            else:
                summary[name] = {
                    "score": val.get("overall", 0),
                }

    risk_indicators = _build_risk_indicators(twin)

    return DigitalTwinDashboardResponse(
        user_id=user_id,
        overall_health=twin.overall_health or "unknown",
        dimension_summary=summary,
        risk_indicators=risk_indicators,
        last_built_at=twin.last_built_at.isoformat() if twin.last_built_at else None,
    )


def _twin_to_response(twin: StudentDigitalTwin) -> DigitalTwinResponse:
    return DigitalTwinResponse(
        user_id=twin.user_id,
        knowledge_state=twin.knowledge_state or {},
        mastery_state=twin.mastery_state or {},
        misconception_state=twin.misconception_state or {},
        retention_state=twin.retention_state or {},
        readiness_state=twin.readiness_state or {},
        intervention_state=twin.intervention_state or {},
        overall_health=twin.overall_health or "unknown",
        confidence=twin.confidence or 0.0,
        last_built_at=twin.last_built_at.isoformat() if twin.last_built_at else None,
        created_at=twin.created_at.isoformat() if twin.created_at else "",
        updated_at=twin.updated_at.isoformat() if twin.updated_at else "",
    )


def _build_risk_indicators(twin: StudentDigitalTwin) -> list[dict]:
    indicators: list[dict] = []

    mc = twin.misconception_state or {}
    for topic, patterns in mc.get("topics", {}).items():
        for pattern in patterns:
            if pattern.get("severity") in ("misconception", "persistent_misconception"):
                indicators.append({
                    "topic": topic,
                    "type": "misconception",
                    "severity": pattern.get("severity", "medium"),
                    "detail": pattern.get("pattern", "")[:100],
                })

    rt = twin.retention_state or {}
    for topic, data in rt.get("topics", {}).items():
        if isinstance(data, dict) and data.get("forgetting_risk") == "high":
            indicators.append({
                "topic": topic,
                "type": "retention",
                "severity": "high",
                "detail": f"No review in {data.get('days_since_review', '?')} days",
            })

    rd = twin.readiness_state or {}
    for topic, data in rd.get("topics", {}).items():
        if isinstance(data, dict) and data.get("risk_level") == "high":
            indicators.append({
                "topic": topic,
                "type": "readiness",
                "severity": "high",
                "detail": f"Readiness score: {data.get('readiness_score', 0)}",
            })

    return indicators
```

- [ ] **Step 4: Register router in main.py**

In `src/main.py`:
- Add `digital_twin` to the imports from `src.api`
- Add `app.include_router(digital_twin.router)` line

- [ ] **Step 5: Run API tests**

Run: `pytest tests/test_digital_twin.py::TestDigitalTwinAPI -v`
Expected: PASS (if async_client fixture exists in conftest.py)

- [ ] **Step 6: Check if async_client fixture exists**

Run: `grep -n "async_client" tests/conftest.py`
If it doesn't exist, add a minimal fixture:

```python
# In tests/conftest.py
@pytest.fixture
async def async_client():
    from httpx import AsyncClient, ASGITransport
    from src.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
```

Run: `pip install httpx` if not installed

Re-run API tests after fixture.

- [ ] **Step 7: Commit**

```bash
git add src/api/digital_twin.py src/main.py tests/test_digital_twin.py
git commit -m "feat: add digital-twin API endpoints (GET, POST rebuild, dashboard)"
```

---

### Task 5: Dashboard Twin Viewer Page

**Files:**
- Create: `dashboard/src/app/digital-twin/page.tsx`
- Modify: `dashboard/src/components/dashboard-v2/SidebarV2.tsx`

- [ ] **Step 1: Create the dashboard page**

```tsx
// dashboard/src/app/digital-twin/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Activity, Brain, Clock, Target, AlertTriangle,
  Shield, RefreshCw, Loader2, TrendingUp,
} from 'lucide-react'
import { DashboardLayout } from '@/components/dashboard-v2'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { getUserId, isAuthenticated } from '@/lib/auth'

export const dynamic = 'force-dynamic'

interface DimensionSummary {
  score?: number
  active?: number
  resolved?: number
  completed?: number
}

interface RiskIndicator {
  topic: string
  type: string
  severity: string
  detail: string
}

interface DashboardData {
  user_id: string
  overall_health: string
  dimension_summary: Record<string, DimensionSummary>
  risk_indicators: RiskIndicator[]
  last_built_at: string | null
}

const DIMENSION_ICONS: Record<string, typeof Activity> = {
  knowledge: Activity,
  mastery: TrendingUp,
  misconceptions: Brain,
  retention: Clock,
  readiness: Target,
  interventions: Shield,
}

const HEALTH_COLORS: Record<string, string> = {
  healthy: 'bg-green-500/10 text-green-400 border-green-500/20',
  needs_attention: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  at_risk: 'bg-red-500/10 text-red-400 border-red-500/20',
}

export default function DigitalTwinPage() {
  const router = useRouter()
  const userId = getUserId()
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [rebuilding, setRebuilding] = useState(false)

  const fetchTwin = async () => {
    if (!userId) return
    setLoading(true)
    try {
      const result = await fetchWithAuth(`/digital-twin/${userId}/dashboard`)
      setData(result)
    } catch {
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  const triggerRebuild = async () => {
    if (!userId) return
    setRebuilding(true)
    try {
      await fetchWithAuth(`/digital-twin/${userId}/rebuild`, { method: 'POST' }, 60000)
      await fetchTwin()
    } catch {
      // ignore
    } finally {
      setRebuilding(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    fetchTwin()
  }, [userId, router])

  if (!isAuthenticated()) return null

  const healthColor = data ? HEALTH_COLORS[data.overall_health] || HEALTH_COLORS.needs_attention : ''

  return (
    <DashboardLayout breadcrumbs={[
      { label: 'Overview', href: '/v2/overview' },
      { label: 'Digital Twin' },
    ]}>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Digital Twin</h1>
            <p className="text-sm text-foreground-muted mt-1">
              Your virtual learner model — knowledge, mastery, misconceptions, retention, readiness, and interventions
            </p>
          </div>
          <button
            onClick={triggerRebuild}
            disabled={rebuilding}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${rebuilding ? 'animate-spin' : ''}`} />
            {rebuilding ? 'Rebuilding...' : 'Rebuild'}
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 animate-spin text-foreground-muted" />
          </div>
        ) : !data ? (
          <div className="text-center py-16 bg-card rounded-xl border border-border">
            <Activity className="w-12 h-12 text-border mx-auto mb-3" />
            <p className="text-foreground-muted font-medium">No digital twin data yet</p>
            <p className="text-sm text-foreground-muted/60 mt-1">
              Complete assessments and activities to build your twin
            </p>
          </div>
        ) : (
          <>
            <div className={`rounded-xl border p-4 ${healthColor}`}>
              <div className="flex items-center gap-3">
                <Shield className="w-6 h-6" />
                <div>
                  <p className="text-sm font-medium capitalize">
                    {data.overall_health.replace(/_/g, ' ')}
                  </p>
                  <p className="text-xs opacity-70">
                    Last updated: {data.last_built_at ? new Date(data.last_built_at).toLocaleString() : 'Never'}
                  </p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(data.dimension_summary).map(([name, summary]) => {
                const Icon = DIMENSION_ICONS[name] || Activity
                return (
                  <div key={name} className="bg-card border border-border rounded-xl p-4">
                    <div className="flex items-center gap-2 text-foreground-muted text-xs mb-3">
                      <Icon className="w-4 h-4" />
                      <span className="font-medium capitalize">{name}</span>
                    </div>
                    {'score' in summary && summary.score !== undefined ? (
                      <div className="flex items-baseline gap-1">
                        <span className="text-2xl font-bold text-foreground">
                          {Math.round(summary.score * 100)}%
                        </span>
                        <span className="text-xs text-foreground-muted">score</span>
                      </div>
                    ) : null}
                    {'active' in summary ? (
                      <div className="text-sm text-foreground">
                        <span className="font-medium">{summary.active}</span>
                        {' '}active{' '}
                        {summary.resolved !== undefined ? (
                          <span className="text-foreground-muted">
                            · {summary.resolved} resolved
                          </span>
                        ) : null}
                        {summary.completed !== undefined ? (
                          <span className="text-foreground-muted">
                            · {summary.completed} completed
                          </span>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                )
              })}
            </div>

            {data.risk_indicators.length > 0 && (
              <div className="bg-card border border-border rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <AlertTriangle className="w-4 h-4 text-red-400" />
                  <h2 className="text-sm font-semibold text-foreground">Risk Indicators</h2>
                </div>
                <div className="space-y-2">
                  {data.risk_indicators.map((r, i) => (
                    <div key={i} className="flex items-start gap-3 p-3 bg-background-secondary rounded-lg">
                      <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                        r.severity === 'high' ? 'bg-red-400' : 'bg-yellow-400'
                      }`} />
                      <div>
                        <p className="text-sm font-medium text-foreground capitalize">
                          {r.type} · {r.topic}
                        </p>
                        <p className="text-xs text-foreground-muted">{r.detail}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </DashboardLayout>
  )
}
```

- [ ] **Step 2: Add Dijital Twin link to SidebarV2**

In `dashboard/src/components/dashboard-v2/SidebarV2.tsx`:
- Add `RefreshCw` to the lucide-react import
- Add nav item: `{ label: 'Digital Twin', href: '/digital-twin', icon: RefreshCw, roles: ['admin', 'teacher', 'student'] }`

- [ ] **Step 3: TypeScript check**

Run: `npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/app/digital-twin/page.tsx dashboard/src/components/dashboard-v2/SidebarV2.tsx
git commit -m "feat: add Digital Twin dashboard viewer page"
```

---

### Task 6: Final Verification

- [ ] **Step 1: Run ruff check**

Run: `ruff check src/core/digital_twin/ src/api/digital_twin.py src/schemas/digital_twin.py`
Expected: All checks passed

- [ ] **Step 2: Run mypy**

Run: `mypy src/core/digital_twin/ src/api/digital_twin.py src/schemas/digital_twin.py`
Expected: Success, no issues found

- [ ] **Step 3: Run all tests**

Run: `pytest tests/test_digital_twin.py -v`
Expected: All tests pass

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/ -v -k "not test_chat_endpoint and not test_quiz_generate_endpoint" | tail -5`
Expected: No regressions

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: final verification for digital twin builder"
```
