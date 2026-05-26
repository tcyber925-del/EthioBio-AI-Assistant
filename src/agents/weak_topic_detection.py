from datetime import datetime, timezone
from typing import Any, cast

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    MisconceptionPattern,
    Question,
    Quiz,
    QuizAttempt,
    RecoveryNotification,
    StudentMastery,
    StudentProfile,
    TopicMasteryHistory,
)

logger = structlog.get_logger()


def calculate_severity(average_score: float) -> str:
    if average_score < 40:
        return "critical"
    elif average_score < 60:
        return "moderate"
    elif average_score < 80:
        return "mild"
    return "good"


def calculate_confidence(attempt_count: int) -> float:
    return min(attempt_count / 3, 1.0)


async def analyze_quiz_attempt(attempt: QuizAttempt, session: AsyncSession) -> None:
    questions_result = await session.execute(
        select(Question).where(Question.quiz_id == attempt.quiz_id)
    )
    questions = questions_result.scalars().all()
    question_map = {str(q.id): q for q in questions}

    topic_correct: dict[str, int] = {}
    topic_total: dict[str, int] = {}
    topic_wrong: dict[str, list[dict[str, Any]]] = {}

    raw_answers: Any = attempt.answers or []
    answers: list[Any] = cast(list[Any], raw_answers) if isinstance(raw_answers, list) else []
    for answer in answers:
        q_id = answer.get("question_id") if isinstance(answer, dict) else answer.question_id
        user_answer = answer.get("answer", "") if isinstance(answer, dict) else answer.answer

        question = question_map.get(q_id)
        if not question:
            continue
        topic = question.topic
        if topic not in topic_total:
            topic_correct[topic] = 0
            topic_total[topic] = 0
            topic_wrong[topic] = []

        topic_total[topic] += 1
        correct_answer = question.correct_answer or ""
        is_correct = user_answer.strip().lower() == correct_answer.strip().lower()
        if is_correct:
            topic_correct[topic] += 1
        else:
            topic_wrong[topic].append({
                "question_id": q_id,
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "question_type": question.question_type,
            })

    quiz_obj = await session.get(Quiz, attempt.quiz_id)
    unit = quiz_obj.topic if quiz_obj else None
    grade_level = quiz_obj.grade_level if quiz_obj else 0

    for topic in topic_total:
        total_q = topic_total[topic]
        correct = topic_correct.get(topic, 0)
        pct = (correct / total_q * 100) if total_q > 0 else 0
        await _update_mastery(attempt.user_id, topic, pct, total_q, correct,
                              unit, grade_level, attempt, session)

        if topic_wrong.get(topic):
            await _detect_misconceptions(attempt.user_id, topic, topic_wrong[topic], session)

    await _update_student_profile_weak_areas(attempt.user_id, session)


async def _update_mastery(user_id: Any, topic: str, pct: float, total_questions: int,
                           correct_count: int, unit: Any, grade_level: int,
                           attempt: QuizAttempt, session: AsyncSession) -> None:
    result = await session.execute(
        select(StudentMastery).where(
            StudentMastery.user_id == user_id,
            StudentMastery.topic == topic,
        )
    )
    mastery = result.scalar_one_or_none()

    old_score = None
    old_severity = None

    if mastery:
        old_score = mastery.average_score
        old_severity = mastery.severity
        new_total = mastery.total_questions_attempted + total_questions
        new_correct = mastery.correct_answers + correct_count
        new_avg = (new_correct / new_total * 100) if new_total > 0 else 0
        mastery.average_score = round(new_avg, 1)
        mastery.total_questions_attempted = new_total
        mastery.correct_answers = new_correct
        mastery.attempt_count += 1
        mastery.severity = calculate_severity(new_avg)
        mastery.confidence = calculate_confidence(mastery.attempt_count)
        mastery.last_assessed_at = attempt.completed_at or attempt.started_at
        if unit and not mastery.unit:
            mastery.unit = unit
        if grade_level and not mastery.grade_level:
            mastery.grade_level = grade_level
    else:
        mastery = StudentMastery(
            user_id=user_id,
            topic=topic,
            unit=unit or "",
            grade_level=grade_level or 0,
            average_score=round(pct, 1),
            attempt_count=1,
            total_questions_attempted=total_questions,
            correct_answers=correct_count,
            severity=calculate_severity(pct),
            confidence=calculate_confidence(1),
            last_assessed_at=attempt.completed_at or attempt.started_at,
        )
        session.add(mastery)

    history_entry = TopicMasteryHistory(
        user_id=user_id,
        topic=topic,
        unit=unit or None,
        grade_level=grade_level or 0,
        average_score=mastery.average_score,
        attempt_count=mastery.attempt_count,
        severity=mastery.severity,
        confidence=mastery.confidence,
        source="quiz",
        source_id=attempt.id,
        recorded_at=mastery.last_assessed_at,
    )
    session.add(history_entry)

    await session.flush()

    if old_score is not None and mastery.average_score > old_score:
        improvement = round(mastery.average_score - old_score, 1)
        if improvement >= 5:
            await _generate_improvement_notification(
                user_id=user_id, topic=topic, event_type="mastery_improvement",
                improvement_pct=improvement,
                message=(
                    f"Great progress in {topic}! Your mastery improved from "
                    f"{old_score:.0f}% to {mastery.average_score:.0f}% (+{improvement:.0f}%). "
                    f"Keep up the excellent work!"
                ),
                old_value=old_score, new_value=mastery.average_score,
                session=session,
            )
        if old_severity and mastery.severity != old_severity:
            severity_rank = {"critical": 0, "moderate": 1, "mild": 2, "good": 3}
            old_rank = severity_rank.get(old_severity, 0)
            new_rank = severity_rank.get(mastery.severity, 0)
            if new_rank > old_rank:
                await _generate_improvement_notification(
                    user_id=user_id, topic=topic, event_type="severity_upgrade",
                    improvement_pct=improvement if improvement >= 0 else None,
                    message=(
                        f"Excellent work! Your understanding of {topic} has improved "
                        f"from {old_severity} to {mastery.severity}. "
                        f"You're making great progress!"
                    ),
                    old_value=old_rank, new_value=new_rank,
                    session=session,
                )


async def _detect_misconceptions(user_id: Any, topic: str,
                                  wrong_details: list[dict[str, Any]],
                                  session: AsyncSession) -> None:
    wrong_group: dict[tuple[str, str], list[str]] = {}
    for detail in wrong_details:
        key = (detail["user_answer"].strip().lower(), detail["correct_answer"].strip().lower())
        if key not in wrong_group:
            wrong_group[key] = []
        wrong_group[key].append(detail["question_id"])

    for (user_ans, correct_ans), question_ids in wrong_group.items():
        if len(question_ids) < 2:
            continue

        existing = await session.execute(
            select(MisconceptionPattern).where(
                MisconceptionPattern.user_id == user_id,
                MisconceptionPattern.topic == topic,
                MisconceptionPattern.common_wrong_answer == user_ans,
                MisconceptionPattern.pattern_type == "wrong_answer",
            )
        )
        pattern = existing.scalar_one_or_none()

        if pattern:
            pattern.frequency += 1
            existing_raw: Any = pattern.related_question_ids or []
            if isinstance(existing_raw, list):
                existing_ids = set(cast(list[str], existing_raw))
            else:
                existing_ids = set()
            existing_ids.update(question_ids)
            pattern.related_question_ids = list(existing_ids)  # type: ignore[assignment]
            pattern.last_detected_at = datetime.now(timezone.utc)
        else:
            pattern = MisconceptionPattern(
                user_id=user_id,
                topic=topic,
                pattern_type="wrong_answer",
                pattern_description=f"Student answers '{user_ans}' instead of '{correct_ans}'",
                frequency=1,
                common_wrong_answer=user_ans,
                related_question_ids=question_ids,
            )
            session.add(pattern)


async def _update_student_profile_weak_areas(user_id: Any, session: AsyncSession) -> None:
    result = await session.execute(
        select(StudentMastery)
        .where(StudentMastery.user_id == user_id)
        .order_by(StudentMastery.average_score.asc())
    )
    masteries = result.scalars().all()
    if not masteries:
        return

    weak_topics = [m.topic for m in masteries if m.severity in ("critical", "moderate")]
    topic_mastery_dict: dict[str, dict[str, Any]] = {}
    for m in masteries:
        topic_mastery_dict[m.topic] = {
            "average_score": m.average_score,
            "severity": m.severity,
            "confidence": m.confidence,
            "attempt_count": m.attempt_count,
        }

    profile_result = await session.execute(
        select(StudentProfile).where(StudentProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()
    if profile:
        profile.weak_areas = weak_topics
        profile.topic_mastery = topic_mastery_dict
        await session.flush()


async def record_mastery_history(
    user_id: Any, topic: str, unit: str | None, grade_level: int,
    session: AsyncSession, source: str = "quiz", source_id: Any = None,
    old_score: float | None = None,
) -> None:
    result = await session.execute(
        select(StudentMastery).where(
            StudentMastery.user_id == user_id,
            StudentMastery.topic == topic,
        )
    )
    mastery = result.scalar_one_or_none()
    if not mastery:
        return

    entry = TopicMasteryHistory(
        user_id=user_id,
        topic=topic,
        unit=unit,
        grade_level=grade_level or 0,
        average_score=mastery.average_score,
        attempt_count=mastery.attempt_count,
        severity=mastery.severity,
        confidence=mastery.confidence,
        source=source,
        source_id=source_id,
        recorded_at=mastery.last_assessed_at,
    )
    session.add(entry)

    if old_score is not None and mastery.average_score > old_score:
        improvement = round(mastery.average_score - old_score, 1)
        if improvement >= 5:
            await _generate_improvement_notification(
                user_id=user_id, topic=topic, event_type="mastery_improvement",
                improvement_pct=improvement,
                message=(
                    f"Great progress in {topic}! Your mastery improved from "
                    f"{old_score:.0f}% to {mastery.average_score:.0f}% (+{improvement:.0f}%). "
                    f"Keep up the excellent work!"
                ),
                old_value=old_score, new_value=mastery.average_score,
                session=session,
            )


async def _generate_improvement_notification(
    user_id: Any, topic: str, event_type: str, improvement_pct: float | None,
    message: str, old_value: float | None = None, new_value: float | None = None,
    session: AsyncSession = None,
) -> None:
    notification = RecoveryNotification(
        user_id=user_id,
        topic=topic,
        event_type=event_type,
        message=message,
        improvement_pct=improvement_pct,
        old_value=old_value,
        new_value=new_value,
        is_read=False,
    )
    session.add(notification)


async def get_weak_topics(user_id: Any, session: AsyncSession) -> list[dict[str, Any]]:
    result = await session.execute(
        select(StudentMastery)
        .where(StudentMastery.user_id == user_id)
        .order_by(StudentMastery.average_score.asc())
    )
    masteries = result.scalars().all()

    misconceptions_result = await session.execute(
        select(MisconceptionPattern)
        .where(
            MisconceptionPattern.user_id == user_id,
            MisconceptionPattern.resolved.is_(False),
        )
        .order_by(MisconceptionPattern.frequency.desc())
    )
    misconceptions = misconceptions_result.scalars().all()

    weak: list[dict[str, Any]] = []
    for m in masteries:
        if m.severity not in ("critical", "moderate", "mild"):
            continue
        topic_misconceptions = [
            {
                "pattern_type": p.pattern_type,
                "description": p.pattern_description,
                "frequency": p.frequency,
            }
            for p in misconceptions
            if p.topic == m.topic
        ]
        weak.append({
            "topic": m.topic,
            "unit": m.unit or "",
            "grade_level": m.grade_level,
            "average_score": m.average_score,
            "attempt_count": m.attempt_count,
            "severity": m.severity,
            "confidence": m.confidence,
            "misconceptions": topic_misconceptions,
            "last_assessed_at": m.last_assessed_at,
        })

    return weak
