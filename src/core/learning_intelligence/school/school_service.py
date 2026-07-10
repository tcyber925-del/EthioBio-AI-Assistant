import asyncio
from collections import Counter
from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.learning_intelligence.readiness.models import (
    ExamReadinessProfile,
)
from src.core.learning_intelligence.readiness.readiness_service import (
    ReadinessService,
)
from src.core.learning_intelligence.school.models import SchoolProfile, TeacherMetric
from src.database.models import ClassGroup, School, SchoolHealthSnapshot

logger = structlog.get_logger()
RISK_HEALTH_THRESHOLD = 40.0


class SchoolService:
    def __init__(self, readiness_service: ReadinessService | None = None):
        self._readiness_service = readiness_service or ReadinessService()

    async def get_school_overview(
        self,
        session: AsyncSession,
        school_id: UUID,
    ) -> SchoolProfile:
        school = await self._load_school(session, school_id)
        if not school:
            return self._empty_profile(school_id)

        class_groups = school.class_groups
        if not class_groups:
            return self._empty_profile(school_id)

        readiness_tasks = [self._fetch_readiness_for_class(session, cg) for cg in class_groups]
        class_results = await asyncio.gather(*readiness_tasks, return_exceptions=True)

        valid_classes = []
        for cg, result in zip(class_groups, class_results):
            if isinstance(result, list):
                valid_classes.append((cg, result))
            elif isinstance(result, Exception):
                logger.warning("class_readiness_failed", class_id=str(cg.id), error=str(result))

        return self._build_school_profile(school, valid_classes)

    async def _load_school(
        self,
        session: AsyncSession,
        school_id: UUID,
    ) -> School | None:
        result = await session.execute(
            select(School)
            .where(School.id == school_id)
            .options(selectinload(School.class_groups).selectinload(ClassGroup.students))
        )
        return result.scalar_one_or_none()

    async def _fetch_readiness_for_class(
        self,
        session: AsyncSession,
        class_group: ClassGroup,
    ) -> list[ExamReadinessProfile]:
        if not class_group.students:
            return []

        tasks = [self._safe_fetch_readiness(session, s.id) for s in class_group.students]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        profiles: list[ExamReadinessProfile] = []
        for r in results:
            if isinstance(r, ExamReadinessProfile):
                profiles.append(r)
            elif isinstance(r, Exception):
                logger.warning(
                    "student_readiness_failed",
                    student_id="unknown",
                    error=str(r),
                )
        return profiles

    async def _safe_fetch_readiness(
        self,
        session: AsyncSession,
        student_id: UUID,
    ) -> ExamReadinessProfile | None:
        try:
            return await self._readiness_service.get_readiness(session, student_id)
        except Exception as e:
            logger.warning(
                "readiness_fetch_failed_for_student",
                student_id=str(student_id),
                error=str(e),
            )
            return None

    def _build_school_profile(
        self,
        school: School,
        valid_classes: list[tuple[ClassGroup, list[ExamReadinessProfile]]],
    ) -> SchoolProfile:
        now = datetime.now(timezone.utc)
        all_profiles: list[ExamReadinessProfile] = []
        teacher_class_map: dict[UUID, list[float]] = {}
        teacher_interventions: dict[UUID, int] = {}
        class_health_map: list[dict] = []

        teacher_profiles: dict[UUID, list[ExamReadinessProfile]] = {}

        for cg, profiles in valid_classes:
            if not profiles:
                continue

            tid = cg.teacher_id
            if tid not in teacher_class_map:
                teacher_class_map[tid] = []
                teacher_interventions[tid] = 0
                teacher_profiles[tid] = []

            teacher_class_map[tid].append(cg)
            teacher_interventions[tid] += sum(len(p.recommended_interventions) for p in profiles)
            teacher_profiles[tid].extend(profiles)
            all_profiles.extend(profiles)

            health = sum(p.overall_readiness for p in profiles) / len(profiles)
            class_risk_count = sum(
                1 for p in profiles if p.overall_readiness < RISK_HEALTH_THRESHOLD
            )
            if health < RISK_HEALTH_THRESHOLD or class_risk_count > len(profiles) // 2:
                class_health_map.append(
                    {
                        "class_id": cg.id,
                        "name": cg.name,
                        "health": round(health, 1),
                        "risk_student_count": class_risk_count,
                    }
                )

        total_students = len(all_profiles)
        avg_health = (
            sum(p.overall_readiness for p in all_profiles) / total_students
            if total_students > 0
            else 0.0
        )

        dist = Counter(p.readiness_band for p in all_profiles)
        health_distribution = {
            "Strong": dist.get("Strong", 0),
            "Ready": dist.get("Ready", 0),
            "Developing": dist.get("Developing", 0),
            "Critical": dist.get("Critical", 0),
        }

        teacher_metrics = []
        for tid, classes in teacher_class_map.items():
            t_profiles = teacher_profiles.get(tid, [])
            student_scores = [p.overall_readiness for p in t_profiles]
            avg = sum(student_scores) / len(student_scores) if student_scores else 0.0
            total_classrooms = len(classes)
            intv_count = teacher_interventions[tid]
            intv_rate = intv_count / total_classrooms if total_classrooms > 0 else 0.0
            teacher_metrics.append(
                TeacherMetric(
                    teacher_id=tid,
                    classroom_count=total_classrooms,
                    avg_student_readiness=round(avg, 1),
                    intervention_rate=round(intv_rate, 1),
                    active_plan_count=total_classrooms,
                )
            )

        return SchoolProfile(
            school_id=school.id,
            generated_at=now,
            total_teachers=len(teacher_class_map),
            total_classrooms=len(valid_classes),
            total_students=total_students,
            avg_health=round(avg_health, 1),
            health_distribution=health_distribution,
            teacher_metrics=teacher_metrics,
            at_risk_classrooms=class_health_map,
        )

    def _empty_profile(self, school_id: UUID) -> SchoolProfile:
        now = datetime.now(timezone.utc)
        return SchoolProfile(
            school_id=school_id,
            generated_at=now,
            total_teachers=0,
            total_classrooms=0,
            total_students=0,
            avg_health=0.0,
            health_distribution={"Strong": 0, "Ready": 0, "Developing": 0, "Critical": 0},
            teacher_metrics=[],
            at_risk_classrooms=[],
        )

    async def create_snapshot(
        self,
        session: AsyncSession,
        school_id: UUID,
    ) -> SchoolHealthSnapshot:
        profile = await self.get_school_overview(session, school_id)
        snapshot = SchoolHealthSnapshot(
            school_id=school_id,
            snapshot_date=datetime.now(timezone.utc),
            avg_health=profile.avg_health,
            total_students=profile.total_students,
            at_risk_count=sum(
                profile.health_distribution.get(b, 0) for b in ("Critical", "Developing")
            ),
        )
        session.add(snapshot)
        await session.commit()
        await session.refresh(snapshot)
        return snapshot

    async def get_district_overview(
        self,
        session: AsyncSession,
    ) -> dict:
        result = await session.execute(select(School))
        schools = list(result.scalars().all())
        if not schools:
            return {
                "total_schools": 0,
                "total_teachers": 0,
                "total_classrooms": 0,
                "total_students": 0,
                "avg_health": 0.0,
                "school_breakdown": [],
            }

        tasks = [self.get_school_overview(session, s.id) for s in schools]
        profiles = await asyncio.gather(*tasks, return_exceptions=True)

        school_data = []
        all_students = 0
        all_classrooms = 0
        all_teachers = 0
        health_scores: list[float] = []

        for school, profile_or_err in zip(schools, profiles):
            if isinstance(profile_or_err, Exception):
                logger.warning(
                    "school_overview_failed",
                    school_id=str(school.id),
                    error=str(profile_or_err),
                )
                continue
            p = profile_or_err
            school_data.append(
                {
                    "school_id": str(school.id),
                    "name": school.name,
                    "avg_health": p.avg_health,
                    "total_students": p.total_students,
                    "total_classrooms": p.total_classrooms,
                    "total_teachers": p.total_teachers,
                }
            )
            all_students += p.total_students
            all_classrooms += p.total_classrooms
            all_teachers += p.total_teachers
            health_scores.append(p.avg_health)

        return {
            "total_schools": len(school_data),
            "total_teachers": all_teachers,
            "total_classrooms": all_classrooms,
            "total_students": all_students,
            "avg_health": (
                round(sum(health_scores) / len(health_scores), 1) if health_scores else 0.0
            ),
            "school_breakdown": school_data,
        }

    async def get_trends(
        self,
        session: AsyncSession,
        school_id: UUID,
        days: int = 30,
    ) -> list[SchoolHealthSnapshot]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await session.execute(
            select(SchoolHealthSnapshot)
            .where(
                SchoolHealthSnapshot.school_id == school_id,
                SchoolHealthSnapshot.snapshot_date >= cutoff,
            )
            .order_by(SchoolHealthSnapshot.snapshot_date)
        )
        return list(result.scalars().all())
