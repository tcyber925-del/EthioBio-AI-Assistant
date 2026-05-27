import os
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.agents.recovery_agent import RecoveryAgent
from src.agents.spaced_repetition import (
    generate_schedule,
    get_all_schedules,
    get_due_reviews,
    update_review,
)
from src.agents.weak_topic_detection import get_weak_topics, record_mastery_history
from src.api.gamification import (
    RECOVERY_MILESTONE_THRESHOLDS,
    XP_SOURCES,
    award_xp,
    check_achievements,
    update_streak,
)
from src.database.models import (
    NotificationPreference,
    RecoveryNotification,
    RecoveryPlan,
    RecoveryTask,
    StudentMastery,
    TopicMasteryHistory,
)
from src.database.session import get_session
from src.llm.router import ModelRouter
from src.notifications.email_service import send_email
from src.schemas.recovery import (
    CompleteTaskResponse,
    CreateRecoveryPlanRequest,
    DueReviewsResponse,
    GenerateRecoveryPlanRequest,
    GenerateRecoveryPlanResponse,
    MasteryHistoryPoint,
    MasteryHistoryResponse,
    RecommendationInfo,
    RecoveryDashboardResponse,
    RecoveryNotificationListResponse,
    RecoveryNotificationResponse,
    RecoveryPlanResponse,
    RecoveryTaskResponse,
    SpacedRepetitionGenerateResponse,
    SpacedRepetitionItem,
    SpacedRepetitionReviewRequest,
    SpacedRepetitionReviewResponse,
    SpacedRepetitionScheduleResponse,
    WeakTopicsResponse,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/recovery", tags=["Recovery"])


@router.post("/plan", response_model=RecoveryPlanResponse)
async def create_recovery_plan(
    request: CreateRecoveryPlanRequest,
    session: AsyncSession = Depends(get_session),
):
    try:
        plan = RecoveryPlan(
            user_id=request.user_id,
            topic=request.topic,
            total_tasks=len(request.tasks),
            status="active",
        )
        session.add(plan)
        await session.flush()

        db_tasks = []
        for t in request.tasks:
            task = RecoveryTask(
                plan_id=plan.id,
                title=t.title,
                task_type=t.task_type,
                description=t.description,
            )
            session.add(task)
            db_tasks.append(task)

        await session.commit()
        await session.refresh(plan)

        return await _build_plan_response(plan, session)
    except Exception as e:
        await session.rollback()
        logger.error("recovery_plan_create_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plan/{user_id}", response_model=list[RecoveryPlanResponse])
async def get_recovery_plans(
    user_id,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await session.execute(
            select(RecoveryPlan)
            .where(RecoveryPlan.user_id == user_id)
            .options(selectinload(RecoveryPlan.tasks))
            .order_by(RecoveryPlan.created_at.desc())
        )
        plans = result.scalars().all()
        return [await _build_plan_response(p, session) for p in plans]
    except Exception as e:
        logger.error("recovery_plans_fetch_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/task/complete", response_model=CompleteTaskResponse)
async def complete_recovery_task(
    task_id,
    user_id,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await session.execute(
            select(RecoveryTask)
            .where(RecoveryTask.id == task_id)
            .options(selectinload(RecoveryTask.plan))
        )
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.is_completed:
            raise HTTPException(status_code=400, detail="Task already completed")
        if task.plan.user_id != user_id:
            raise HTTPException(status_code=403, detail="Task does not belong to this user")

        task.is_completed = True
        task.completed_at = datetime.now(timezone.utc)

        xp_amount = XP_SOURCES.get("recovery_task_completion", 40)
        task.xp_awarded = xp_amount

        plan = task.plan
        plan.completed_tasks += 1
        if plan.completed_tasks >= plan.total_tasks:
            plan.status = "completed"

        gam, _, level_up = await award_xp(
            user_id, "recovery_task_completion", xp_amount,
            {"task_id": str(task_id), "plan_id": str(plan.id), "topic": plan.topic},
            session,
        )

        milestone_bonus = 0
        completed = plan.completed_tasks
        if completed in RECOVERY_MILESTONE_THRESHOLDS:
            milestone_bonus = RECOVERY_MILESTONE_THRESHOLDS[completed]
            gam, _, _ = await award_xp(
                user_id, "recovery_milestone", milestone_bonus,
                {"plan_id": str(plan.id), "completed_tasks": completed, "topic": plan.topic},
                session,
            )

        await update_streak(user_id, session)
        await check_achievements(user_id, gam, session)

        old_mastery_result = await session.execute(
            select(StudentMastery).where(
                StudentMastery.user_id == user_id,
                StudentMastery.topic == plan.topic,
            )
        )
        old_mastery = old_mastery_result.scalar_one_or_none()
        old_score = old_mastery.average_score if old_mastery else None

        await record_mastery_history(
            user_id=user_id, topic=plan.topic, unit=None,
            grade_level=0, session=session, source="task_completion",
            source_id=task.id, old_score=old_score,
        )

        # Milestone email notification
        try:
            prefs_result = await session.execute(
                select(NotificationPreference).where(NotificationPreference.user_id == user_id)
            )
            prefs = prefs_result.scalar_one_or_none()

            if prefs and prefs.milestone_alerts and prefs.email_verified:
                current_result = await session.execute(
                    select(StudentMastery).where(
                        StudentMastery.user_id == user_id,
                        StudentMastery.topic == plan.topic,
                    )
                )
                current_mastery = current_result.scalar_one_or_none()
                current_score = current_mastery.average_score if current_mastery else None

                if old_score is not None and current_score is not None:
                    improvement = current_score - old_score
                    if improvement >= 10.0:
                        template_dir = os.path.join(
                            os.path.dirname(__file__), "..", "notifications", "templates",
                        )
                        env = Environment(loader=FileSystemLoader(template_dir))
                        template = env.get_template("milestone_alert.html")
                        html = template.render(
                            title="Milestone Achieved!",
                            message=(
                                f"You improved your {plan.topic} mastery"
                                f" by {improvement:.0f}%!"
                            ),
                            improvement_pct=f"{improvement:.0f}",
                            topic=plan.topic,
                        )
                        subject = f"Milestone: +{improvement:.0f}% in {plan.topic}"
                        await send_email(prefs.email, subject, html)
        except Exception as e:
            logger.error("recovery_milestone_email_error", error=str(e))

        await session.commit()

        total = xp_amount + milestone_bonus
        progress = round(plan.completed_tasks / max(plan.total_tasks, 1) * 100, 1)

        if plan.status == "completed":
            notification = RecoveryNotification(
                user_id=user_id,
                topic=plan.topic,
                event_type="plan_completed",
                message=(
                    f"Congratulations! You completed the recovery plan for {plan.topic}! "
                    f"All {plan.total_tasks} tasks finished. "
                    f"Great dedication to your learning!"
                ),
                improvement_pct=progress,
            )
            session.add(notification)

        return CompleteTaskResponse(
            task_id=task.id,
            plan_id=plan.id,
            xp_awarded=xp_amount,
            milestone_bonus=milestone_bonus,
            total_xp=total,
            level_up=level_up,
            new_level=gam.level,
            plan_completed=plan.status == "completed",
            progress_pct=progress,
        )
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("recovery_task_complete_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-generate/{user_id}", response_model=GenerateRecoveryPlanResponse)
async def auto_generate_recovery_plan(
    user_id,
    request: GenerateRecoveryPlanRequest = None,
    session: AsyncSession = Depends(get_session),
):
    if request is None:
        request = GenerateRecoveryPlanRequest()
    try:
        router = ModelRouter()
        agent = RecoveryAgent(router)
        result = await agent.generate_plan(
            user_id=user_id,
            session=session,
            topic_filter=request.topic_filter,
        )
        return GenerateRecoveryPlanResponse(
            plan=result.get("plan"),
            error=result.get("error"),
        )
    except Exception as e:
        logger.error("auto_generate_recovery_plan_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weak-topics/{user_id}", response_model=WeakTopicsResponse)
async def get_weak_topics_endpoint(user_id, session: AsyncSession = Depends(get_session)):
    try:
        weak_topics = await get_weak_topics(user_id, session)
        return WeakTopicsResponse(
            user_id=user_id,
            weak_topics=weak_topics,
            total_weak_topics=len(weak_topics),
        )
    except Exception as e:
        logger.error("weak_topics_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{user_id}/{topic}", response_model=MasteryHistoryResponse)
async def get_mastery_history(user_id, topic: str, session: AsyncSession = Depends(get_session)):
    try:
        result = await session.execute(
            select(TopicMasteryHistory)
            .where(
                TopicMasteryHistory.user_id == user_id,
                TopicMasteryHistory.topic == topic,
            )
            .order_by(TopicMasteryHistory.recorded_at.asc())
        )
        records = result.scalars().all()
        return MasteryHistoryResponse(
            user_id=user_id,
            topic=topic,
            history=[
                MasteryHistoryPoint(
                    average_score=r.average_score,
                    attempt_count=r.attempt_count,
                    severity=r.severity,
                    confidence=r.confidence,
                    source=r.source,
                    recorded_at=r.recorded_at,
                )
                for r in records
            ],
        )
    except Exception as e:
        logger.error("mastery_history_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/{user_id}", response_model=RecoveryDashboardResponse)
async def get_recovery_dashboard(user_id, session: AsyncSession = Depends(get_session)):
    try:
        weak_topics = await get_weak_topics(user_id, session)

        plans_result = await session.execute(
            select(RecoveryPlan)
            .where(RecoveryPlan.user_id == user_id, RecoveryPlan.status == "active")
            .options(selectinload(RecoveryPlan.tasks))
            .order_by(RecoveryPlan.created_at.desc())
        )
        plans = plans_result.scalars().all()
        plan_responses = [await _build_plan_response(p, session) for p in plans]

        recommendations: list[RecommendationInfo] = []
        for wt in weak_topics:
            if wt["severity"] == "critical":
                recommendations.append(RecommendationInfo(
                    type="generate_plan",
                    message=(
                        f"Generate a recovery plan for {wt['topic']}"
                        f" (severity: critical, {wt['average_score']:.0f}% average)"
                    ),
                    priority="high",
                ))
            elif wt["severity"] == "moderate" and wt["confidence"] >= 0.5:
                recommendations.append(RecommendationInfo(
                    type="practice_quiz",
                    message=(
                        f"Practice {wt['topic']} with targeted quizzes"
                        f" ({wt['average_score']:.0f}% average)"
                    ),
                    priority="medium",
                ))
            if wt.get("misconceptions"):
                for mc in wt["misconceptions"]:
                    suffix = "s" if mc["frequency"] > 1 else ""
                    recommendations.append(RecommendationInfo(
                        type="review_misconception",
                        message=(
                            f"Review '{mc['pattern_type']}' misconception"
                            f" in {wt['topic']} ({mc['frequency']} occurrence{suffix})"
                        ),
                        priority="medium",
                    ))

        if recommendations:
            for plan_resp in plan_responses:
                if plan_resp.status == "active":
                    recommendations.append(RecommendationInfo(
                        type="continue_plan",
                        message=(
                            f"Continue {plan_resp.topic} recovery plan"
                            f" ({plan_resp.completed_tasks}/{plan_resp.total_tasks}"
                            f" tasks completed)"
                        ),
                        priority="medium",
                    ))

        recommendations.sort(key=lambda r: {"high": 0, "medium": 1, "low": 2}[r.priority])

        due_items = await get_due_reviews(user_id, session)

        notifications_result = await session.execute(
            select(RecoveryNotification)
            .where(
                RecoveryNotification.user_id == user_id,
                RecoveryNotification.is_read == False,  # noqa: E712
            )
            .order_by(RecoveryNotification.created_at.desc())
            .limit(10)
        )
        unread_notifications = notifications_result.scalars().all()

        return RecoveryDashboardResponse(
            user_id=user_id,
            weak_topics=weak_topics,
            total_weak_topics=len(weak_topics),
            active_plans=plan_responses,
            total_active_plans=len(plan_responses),
            recommendations=recommendations,
            due_reviews=[SpacedRepetitionItem(**i) for i in due_items],
            total_due_reviews=len(due_items),
            unread_notifications=len(unread_notifications),
            notifications=[
                RecoveryNotificationResponse(
                    id=n.id,
                    topic=n.topic,
                    event_type=n.event_type,
                    message=n.message,
                    improvement_pct=n.improvement_pct,
                    old_value=n.old_value,
                    new_value=n.new_value,
                    is_read=n.is_read,
                    created_at=n.created_at,
                )
                for n in unread_notifications
            ],
        )
    except Exception as e:
        logger.error("recovery_dashboard_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schedule/{user_id}", response_model=SpacedRepetitionScheduleResponse)
async def get_spaced_repetition_schedule(user_id, session: AsyncSession = Depends(get_session)):
    try:
        items = await get_all_schedules(user_id, session)
        return SpacedRepetitionScheduleResponse(
            user_id=user_id,
            total_items=len(items),
            items=[SpacedRepetitionItem(**i) for i in items],
        )
    except Exception as e:
        logger.error("spaced_repetition_schedule_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schedule/due/{user_id}", response_model=DueReviewsResponse)
async def get_due_reviews_endpoint(user_id, session: AsyncSession = Depends(get_session)):
    try:
        items = await get_due_reviews(user_id, session)
        return DueReviewsResponse(
            user_id=user_id,
            total_due=len(items),
            items=[SpacedRepetitionItem(**i) for i in items],
        )
    except Exception as e:
        logger.error("due_reviews_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule/generate/{user_id}", response_model=SpacedRepetitionGenerateResponse)
async def generate_spaced_repetition_schedule(
    user_id, session: AsyncSession = Depends(get_session),
):
    try:
        items = await generate_schedule(user_id, session)
        return SpacedRepetitionGenerateResponse(
            user_id=user_id,
            total_generated=len(items),
            items=items,
        )
    except Exception as e:
        logger.error("spaced_repetition_generate_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule/review", response_model=SpacedRepetitionReviewResponse)
async def spaced_repetition_review(request: SpacedRepetitionReviewRequest,
                                   session: AsyncSession = Depends(get_session)):
    try:
        result = await update_review(request.user_id, request.topic, request.new_score, session)
        if not result:
            raise HTTPException(status_code=404, detail="Schedule not found")
        return SpacedRepetitionReviewResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("spaced_repetition_review_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/{user_id}", response_model=RecoveryNotificationListResponse)
async def get_recovery_notifications(
    user_id,
    unread_only: bool = False,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
):
    try:
        stmt = (
            select(RecoveryNotification)
            .where(RecoveryNotification.user_id == user_id)
            .order_by(RecoveryNotification.created_at.desc())
        )
        if unread_only:
            stmt = stmt.where(RecoveryNotification.is_read == False)  # noqa: E712
        result = await session.execute(stmt.limit(limit))
        notifications = result.scalars().all()

        unread_result = await session.execute(
            select(RecoveryNotification)
            .where(
                RecoveryNotification.user_id == user_id,
                RecoveryNotification.is_read == False,  # noqa: E712
            )
        )
        total_unread = len(unread_result.scalars().all())

        return RecoveryNotificationListResponse(
            user_id=user_id,
            notifications=[
                RecoveryNotificationResponse(
                    id=n.id,
                    topic=n.topic,
                    event_type=n.event_type,
                    message=n.message,
                    improvement_pct=n.improvement_pct,
                    old_value=n.old_value,
                    new_value=n.new_value,
                    is_read=n.is_read,
                    created_at=n.created_at,
                )
                for n in notifications
            ],
            total_unread=total_unread,
            total=len(notifications),
        )
    except Exception as e:
        logger.error("recovery_notifications_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await session.execute(
            select(RecoveryNotification).where(RecoveryNotification.id == notification_id)
        )
        notification = result.scalar_one_or_none()
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        notification.is_read = True
        await session.commit()
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("mark_notification_read_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/notifications/read-all/{user_id}")
async def mark_all_notifications_read(
    user_id,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await session.execute(
            select(RecoveryNotification)
            .where(
                RecoveryNotification.user_id == user_id,
                RecoveryNotification.is_read == False,  # noqa: E712
            )
        )
        notifications = result.scalars().all()
        for n in notifications:
            n.is_read = True
        await session.commit()
        return {"status": "ok", "marked": len(notifications)}
    except Exception as e:
        await session.rollback()
        logger.error("mark_all_notifications_read_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


async def _build_plan_response(plan: RecoveryPlan, session: AsyncSession) -> RecoveryPlanResponse:
    tasks = plan.tasks or []
    progress = round(plan.completed_tasks / max(plan.total_tasks, 1) * 100, 1)
    return RecoveryPlanResponse(
        id=plan.id,
        user_id=plan.user_id,
        topic=plan.topic,
        total_tasks=plan.total_tasks,
        completed_tasks=plan.completed_tasks,
        status=plan.status,
        progress_pct=progress,
        tasks=[
            RecoveryTaskResponse(
                id=t.id,
                plan_id=t.plan_id,
                title=t.title,
                task_type=t.task_type,
                description=t.description,
                is_completed=t.is_completed,
                completed_at=t.completed_at,
                xp_awarded=t.xp_awarded,
                created_at=t.created_at,
            )
            for t in tasks
        ],
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )
