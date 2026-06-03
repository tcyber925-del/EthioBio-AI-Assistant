from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.auth import get_current_user
from src.core.learning_intelligence.teacher import TeacherService
from src.database.models import ClassEnrollment, ClassGroup, User
from src.database.session import get_session

logger = structlog.get_logger()
router = APIRouter(prefix="/teacher", tags=["Teacher"])

teacher_service = TeacherService()


class CreateClassroomRequest(BaseModel):
    name: str
    grade_level: int
    student_ids: list[UUID] = []


class EnrollStudentsRequest(BaseModel):
    student_ids: list[UUID]


class ClassroomListItem(BaseModel):
    id: UUID
    name: str
    grade_level: int
    student_count: int


class RosterStudent(BaseModel):
    student_id: UUID
    readiness_score: float
    readiness_band: str
    has_risk_topics: bool


class ClassroomRoster(BaseModel):
    id: UUID
    name: str
    students: list[RosterStudent]


async def _verify_teacher_owns_classroom(
    session: AsyncSession,
    classroom_id: UUID,
    teacher_id: UUID,
) -> ClassGroup:
    result = await session.execute(
        select(ClassGroup).where(
            ClassGroup.id == classroom_id,
        )
    )
    class_group = result.scalar_one_or_none()
    if not class_group or class_group.teacher_id != teacher_id:
        raise HTTPException(status_code=404, detail="Classroom not found")
    return class_group


@router.post("/classrooms")
async def create_classroom(
    body: CreateClassroomRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    class_group = ClassGroup(
        name=body.name,
        grade_level=body.grade_level,
        teacher_id=current_user.id,
    )
    session.add(class_group)
    await session.flush()

    if body.student_ids:
        await _enroll_students(
            session, class_group.id, body.student_ids
        )

    await session.commit()
    return {
        "id": class_group.id,
        "name": class_group.name,
        "grade_level": class_group.grade_level,
        "student_count": len(body.student_ids),
    }


@router.get("/classrooms")
async def list_classrooms(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(ClassGroup)
        .where(ClassGroup.teacher_id == current_user.id)
        .options(selectinload(ClassGroup.students))
    )
    classes = result.scalars().all()
    return [
        ClassroomListItem(
            id=c.id,
            name=c.name,
            grade_level=c.grade_level,
            student_count=len(c.students),
        )
        for c in classes
    ]


@router.get("/classrooms/{classroom_id}")
async def get_classroom_roster(
    classroom_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    class_group = await _verify_teacher_owns_classroom(
        session, classroom_id, current_user.id
    )
    if not class_group.students:
        return ClassroomRoster(
            id=class_group.id,
            name=class_group.name,
            students=[],
        )

    roster_students: list[RosterStudent] = []
    from src.core.learning_intelligence.readiness import ReadinessService

    readiness_svc = ReadinessService()
    for student in class_group.students:
        try:
            profile = await readiness_svc.get_readiness(session, student.id)
            roster_students.append(
                RosterStudent(
                    student_id=student.id,
                    readiness_score=profile.overall_readiness,
                    readiness_band=profile.readiness_band,
                    has_risk_topics=len(profile.risk_topics) > 0,
                )
            )
        except Exception:
            roster_students.append(
                RosterStudent(
                    student_id=student.id,
                    readiness_score=0.0,
                    readiness_band="Unknown",
                    has_risk_topics=False,
                )
            )

    return ClassroomRoster(
        id=class_group.id,
        name=class_group.name,
        students=roster_students,
    )


@router.post("/classrooms/{classroom_id}/enroll")
async def enroll_students(
    classroom_id: UUID,
    body: EnrollStudentsRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _verify_teacher_owns_classroom(
        session, classroom_id, current_user.id
    )

    if not body.student_ids:
        raise HTTPException(
            status_code=400, detail="student_ids list is empty"
        )

    for sid in body.student_ids:
        existing = await session.execute(
            select(ClassEnrollment).where(
                ClassEnrollment.class_id == classroom_id,
                ClassEnrollment.student_id == sid,
            )
        )
        if existing.scalar_one_or_none():
            continue

        enrollment = ClassEnrollment(
            class_id=classroom_id,
            student_id=sid,
        )
        session.add(enrollment)

    await session.commit()
    return {"enrolled": len(body.student_ids)}


@router.get("/classrooms/{classroom_id}/overview")
async def get_classroom_overview(
    classroom_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _verify_teacher_owns_classroom(
        session, classroom_id, current_user.id
    )
    profile = await teacher_service.get_classroom_overview(
        session, classroom_id
    )
    return profile


@router.get("/classrooms/{classroom_id}/risk-students")
async def get_risk_students(
    classroom_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _verify_teacher_owns_classroom(
        session, classroom_id, current_user.id
    )
    profile = await teacher_service.get_classroom_overview(
        session, classroom_id
    )
    return profile.risk_students


@router.get("/classrooms/{classroom_id}/interventions")
async def get_interventions(
    classroom_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _verify_teacher_owns_classroom(
        session, classroom_id, current_user.id
    )
    profile = await teacher_service.get_classroom_overview(
        session, classroom_id
    )
    return profile.intervention_candidates


@router.get("/classrooms/{classroom_id}/mastery-heatmap")
async def get_mastery_heatmap(
    classroom_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _verify_teacher_owns_classroom(
        session, classroom_id, current_user.id
    )
    profile = await teacher_service.get_classroom_overview(
        session, classroom_id
    )
    return profile.mastery_heatmap


async def _enroll_students(
    session: AsyncSession,
    class_id: UUID,
    student_ids: list[UUID],
) -> None:
    for sid in student_ids:
        existing = await session.execute(
            select(ClassEnrollment).where(
                ClassEnrollment.class_id == class_id,
                ClassEnrollment.student_id == sid,
            )
        )
        if existing.scalar_one_or_none():
            continue
        enrollment = ClassEnrollment(
            class_id=class_id,
            student_id=sid,
        )
        session.add(enrollment)
