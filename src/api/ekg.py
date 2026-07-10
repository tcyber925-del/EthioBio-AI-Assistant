from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.knowledge_graph import GraphReasoningEngine, RelationshipBuilder
from src.database.models import CurriculumTopic, TopicPrerequisite
from src.database.session import get_session

logger = structlog.get_logger()
router = APIRouter(prefix="/ekg", tags=["Knowledge Graph"])

builder = RelationshipBuilder()
engine = GraphReasoningEngine()


class PrerequisiteCreate(BaseModel):
    topic_id: UUID
    prerequisite_topic_id: UUID
    relationship_type: str = "prerequisite"


class PrerequisiteBatchCreate(BaseModel):
    topic_id: UUID
    prerequisite_ids: list[UUID]


class PrerequisiteResponse(BaseModel):
    id: UUID
    topic_id: UUID
    prerequisite_topic_id: UUID
    relationship_type: str
    grade_level: int

    @staticmethod
    def from_orm(p: TopicPrerequisite) -> "PrerequisiteResponse":
        return PrerequisiteResponse(
            id=p.id,
            topic_id=p.topic_id,
            prerequisite_topic_id=p.prerequisite_topic_id,
            relationship_type=p.relationship_type,
            grade_level=p.grade_level,
        )


class GraphNode(BaseModel):
    node_id: str
    topic: str | None = None
    unit: str | None = None
    grade_level: int | None = None
    relationship_type: str | None = None
    depth: int | None = None


class GapAnalysisItem(BaseModel):
    node_id: str
    topic: str | None = None
    unit: str | None = None
    grade_level: int | None = None
    relationship_type: str | None = None
    depth: int | None = None
    user_score: float | None = None


@router.post("/prerequisites", response_model=PrerequisiteResponse)
async def create_prerequisite(
    body: PrerequisiteCreate,
    db: AsyncSession = Depends(get_session),
):
    try:
        prereq = await builder.add_prerequisite(
            db=db,
            topic_id=body.topic_id,
            prerequisite_topic_id=body.prerequisite_topic_id,
            relationship_type=body.relationship_type,
        )
        await db.commit()
        return PrerequisiteResponse.from_orm(prereq)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error("prerequisite_create_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prerequisites/batch")
async def create_prerequisites_batch(
    body: PrerequisiteBatchCreate,
    db: AsyncSession = Depends(get_session),
):
    try:
        created = await builder.add_batch(
            db=db,
            topic_id=body.topic_id,
            prerequisite_ids=body.prerequisite_ids,
        )
        await db.commit()
        return {
            "created": len(created),
            "prerequisites": [PrerequisiteResponse.from_orm(p) for p in created],
        }
    except Exception as e:
        await db.rollback()
        logger.error("prerequisite_batch_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prerequisites/{topic_id}", response_model=list[PrerequisiteResponse])
async def get_prerequisites(
    topic_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    try:
        prereqs = await builder.get_prerequisites(db=db, topic_id=topic_id)
        return [PrerequisiteResponse.from_orm(p) for p in prereqs]
    except Exception as e:
        logger.error("prerequisites_get_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dependents/{topic_id}", response_model=list[PrerequisiteResponse])
async def get_dependents(
    topic_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    try:
        deps = await builder.get_dependents(db=db, topic_id=topic_id)
        return [PrerequisiteResponse.from_orm(p) for p in deps]
    except Exception as e:
        logger.error("dependents_get_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/prerequisites/{prereq_id}")
async def delete_prerequisite(
    prereq_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    try:
        success = await builder.remove(db=db, prereq_id=prereq_id)
        await db.commit()
        if not success:
            raise HTTPException(status_code=404, detail="Prerequisite not found")
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("prerequisite_delete_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chain/{topic_id}/prerequisites", response_model=list[GraphNode])
async def prerequisite_chain(
    topic_id: UUID,
    max_depth: int = 5,
    db: AsyncSession = Depends(get_session),
):
    try:
        chain = await engine.get_prerequisite_chain(db=db, topic_id=topic_id, max_depth=max_depth)
        return [GraphNode(**n) for n in chain]
    except Exception as e:
        logger.error("prerequisite_chain_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chain/{topic_id}/dependents", response_model=list[GraphNode])
async def dependent_chain(
    topic_id: UUID,
    max_depth: int = 5,
    db: AsyncSession = Depends(get_session),
):
    try:
        chain = await engine.get_dependent_chain(db=db, topic_id=topic_id, max_depth=max_depth)
        return [GraphNode(**n) for n in chain]
    except Exception as e:
        logger.error("dependent_chain_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gap-analysis/{topic_id}/{user_id}", response_model=list[GapAnalysisItem])
async def prerequisite_gap_analysis(
    topic_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    try:
        gaps = await engine.get_prerequisite_gap_analysis(
            db=db,
            topic_id=topic_id,
            user_id=user_id,
        )
        return [GapAnalysisItem(**g) for g in gaps]
    except Exception as e:
        logger.error("gap_analysis_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics")
async def list_topics(
    grade_level: int | None = None,
    db: AsyncSession = Depends(get_session),
):
    try:
        stmt = select(CurriculumTopic).order_by(
            CurriculumTopic.grade_level,
            CurriculumTopic.unit,
            CurriculumTopic.topic,
        )
        if grade_level is not None:
            stmt = stmt.where(CurriculumTopic.grade_level == grade_level)
        result = await db.execute(stmt)
        topics = result.scalars().all()
        return [
            {
                "id": str(t.id),
                "grade_level": t.grade_level,
                "unit": t.unit,
                "topic": t.topic,
                "subtopic": t.subtopic,
            }
            for t in topics
        ]
    except Exception as e:
        logger.error("topics_list_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
