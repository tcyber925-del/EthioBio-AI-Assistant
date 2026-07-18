from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.auth import get_current_user
from src.core.learning_intelligence.school import SchoolService
from src.core.learning_intelligence.teacher import TeacherService
from src.database.models import (
    ClassEnrollment,
    ClassGroup,
    LessonPlan,
    ModelRoutingLog,
    Quiz,
    QuizAttempt,
    School,
    User,
    UserRole,
)
from src.database.session import get_session

logger = structlog.get_logger()
router = APIRouter(prefix="/teacher", tags=["Teacher"])

teacher_service = TeacherService()
school_service = SchoolService()


class CreateSchoolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str


class CreateClassroomRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    grade_level: int
    student_ids: list[UUID] = []


class EnrollStudentsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
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
        await _enroll_students(session, class_group.id, body.student_ids)

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
    class_group = await _verify_teacher_owns_classroom(session, classroom_id, current_user.id)
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
    await _verify_teacher_owns_classroom(session, classroom_id, current_user.id)

    if not body.student_ids:
        raise HTTPException(status_code=400, detail="student_ids list is empty")

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
    await _verify_teacher_owns_classroom(session, classroom_id, current_user.id)
    profile = await teacher_service.get_classroom_overview(session, classroom_id)
    return profile


@router.get("/classrooms/{classroom_id}/risk-students")
async def get_risk_students(
    classroom_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _verify_teacher_owns_classroom(session, classroom_id, current_user.id)
    profile = await teacher_service.get_classroom_overview(session, classroom_id)
    return profile.risk_students


@router.get("/classrooms/{classroom_id}/interventions")
async def get_interventions(
    classroom_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _verify_teacher_owns_classroom(session, classroom_id, current_user.id)
    profile = await teacher_service.get_classroom_overview(session, classroom_id)
    return profile.intervention_candidates


@router.get("/classrooms/{classroom_id}/mastery-heatmap")
async def get_mastery_heatmap(
    classroom_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _verify_teacher_owns_classroom(session, classroom_id, current_user.id)
    profile = await teacher_service.get_classroom_overview(session, classroom_id)
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


@router.get("/dashboard")
async def teacher_dashboard(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    try:
        user_count = await session.scalar(select(func.count(User.id)))
        teacher_count = await session.scalar(
            select(func.count(User.id)).where(User.role == UserRole.teacher)
        )
        student_count = await session.scalar(
            select(func.count(User.id)).where(User.role == UserRole.student)
        )
        quiz_count = await session.scalar(select(func.count(Quiz.id)))
        lesson_count = await session.scalar(select(func.count(LessonPlan.id)))
        attempt_count = await session.scalar(select(func.count(QuizAttempt.id)))

        latest_logs = await session.execute(
            select(ModelRoutingLog).order_by(ModelRoutingLog.created_at.desc()).limit(20)
        )
        logs = latest_logs.scalars().all()

        return {
            "users": user_count or 0,
            "teachers": teacher_count or 0,
            "students": student_count or 0,
            "quizzes": quiz_count or 0,
            "lesson_plans": lesson_count or 0,
            "quiz_attempts": attempt_count or 0,
            "recent_logs": [
                {
                    "id": str(log.id),
                    "request_type": log.request_type,
                    "model_used": log.model_used,
                    "success": log.success,
                    "latency_ms": log.latency_ms,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
        }
    except Exception as e:
        logger.error("teacher_dashboard_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


def _require_admin(current_user: User) -> None:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/district/overview")
async def get_district_overview(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    return await school_service.get_district_overview(session)


@router.get("/schools")
async def list_schools(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    result = await session.execute(select(School))
    schools = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "created_at": s.created_at.isoformat(),
        }
        for s in schools
    ]


@router.get("/schools/{school_id}/overview")
async def get_school_overview(
    school_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    profile = await school_service.get_school_overview(session, school_id)
    if profile.total_students == 0:
        raise HTTPException(status_code=404, detail="School not found or has no data")
    return profile


@router.post("/schools/{school_id}/snapshot")
async def create_school_snapshot(
    school_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    snapshot = await school_service.create_snapshot(session, school_id)
    return {
        "snapshot_id": snapshot.id,
        "school_id": snapshot.school_id,
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "avg_health": snapshot.avg_health,
        "total_students": snapshot.total_students,
        "at_risk_count": snapshot.at_risk_count,
    }


@router.get("/schools/{school_id}/trends")
async def get_school_trends(
    school_id: UUID,
    days: int = 30,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    snapshots = await school_service.get_trends(session, school_id, days=days)
    return [
        {
            "snapshot_date": s.snapshot_date.isoformat(),
            "avg_health": s.avg_health,
            "total_students": s.total_students,
            "at_risk_count": s.at_risk_count,
        }
        for s in snapshots
    ]


@router.post("/schools")
async def create_school(
    body: CreateSchoolRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    school = School(name=body.name)
    session.add(school)
    await session.commit()
    await session.refresh(school)
    return {
        "id": str(school.id),
        "name": school.name,
        "created_at": school.created_at.isoformat() if school.created_at else None,
    }
