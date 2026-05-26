from datetime import datetime

from src.api.gamification import RECOVERY_MILESTONE_THRESHOLDS, XP_SOURCES
from src.schemas.gamification import RecoveryProgressResponse


def test_recovery_xp_source_exists():
    assert "recovery_task_completion" in XP_SOURCES
    assert XP_SOURCES["recovery_task_completion"] == 40


def test_recovery_milestone_xp_source_exists():
    assert "recovery_milestone" in XP_SOURCES
    assert XP_SOURCES["recovery_milestone"] == 50


def test_recovery_milestone_thresholds():
    assert RECOVERY_MILESTONE_THRESHOLDS[3] == 30
    assert RECOVERY_MILESTONE_THRESHOLDS[5] == 50
    assert RECOVERY_MILESTONE_THRESHOLDS[10] == 100
    assert RECOVERY_MILESTONE_THRESHOLDS[15] == 150


def test_recovery_progress_response_schema():
    resp = RecoveryProgressResponse(
        active_plans=2,
        total_tasks=10,
        completed_tasks=4,
        overall_progress_pct=40.0,
    )
    assert resp.active_plans == 2
    assert resp.total_tasks == 10
    assert resp.completed_tasks == 4
    assert resp.overall_progress_pct == 40.0


def test_recovery_progress_response_empty():
    resp = RecoveryProgressResponse()
    assert resp.active_plans == 0
    assert resp.total_tasks == 0
    assert resp.completed_tasks == 0
    assert resp.overall_progress_pct == 0.0


def test_complete_task_response_schema():
    from src.schemas.recovery import CompleteTaskResponse
    resp = CompleteTaskResponse(
        task_id="00000000-0000-0000-0000-000000000001",
        plan_id="00000000-0000-0000-0000-000000000002",
        xp_awarded=40,
        milestone_bonus=0,
        total_xp=40,
        level_up=False,
        new_level=0,
        plan_completed=False,
        progress_pct=50.0,
    )
    assert resp.xp_awarded == 40
    assert resp.total_xp == 40
    assert resp.progress_pct == 50.0
    assert resp.plan_completed is False
    assert resp.level_up is False


def test_recovery_plan_response_schema():
    from datetime import datetime

    from src.schemas.recovery import RecoveryPlanResponse, RecoveryTaskResponse
    now = datetime.now()
    task = RecoveryTaskResponse(
        id="00000000-0000-0000-0000-000000000003",
        plan_id="00000000-0000-0000-0000-000000000004",
        title="Review Cell Division",
        task_type="quiz",
        created_at=now,
    )
    plan = RecoveryPlanResponse(
        id="00000000-0000-0000-0000-000000000004",
        user_id="00000000-0000-0000-0000-000000000005",
        topic="Cell Biology",
        total_tasks=5,
        completed_tasks=2,
        status="active",
        progress_pct=40.0,
        tasks=[task],
        created_at=now,
        updated_at=now,
    )
    assert plan.topic == "Cell Biology"
    assert plan.total_tasks == 5
    assert plan.completed_tasks == 2
    assert plan.progress_pct == 40.0
    assert len(plan.tasks) == 1
    assert plan.tasks[0].title == "Review Cell Division"
    assert plan.tasks[0].is_completed is False


def test_gamification_profile_response_has_recovery():
    from src.schemas.gamification import GamificationProfileResponse
    resp = GamificationProfileResponse(
        user_id="00000000-0000-0000-0000-000000000006",
        total_xp=100,
        level=2,
        current_streak=1,
        longest_streak=3,
        next_level_xp=150,
        progress_pct=50.0,
        recovery_progress=None,
    )
    assert hasattr(resp, "recovery_progress")
    assert resp.recovery_progress is None

    rec_progress = RecoveryProgressResponse(
        active_plans=1, total_tasks=3, completed_tasks=1, overall_progress_pct=33.3,
    )
    resp_with_recovery = GamificationProfileResponse(
        user_id="00000000-0000-0000-0000-000000000006",
        total_xp=100,
        level=2,
        current_streak=1,
        longest_streak=3,
        next_level_xp=150,
        progress_pct=50.0,
        recovery_progress=rec_progress,
    )
    assert resp_with_recovery.recovery_progress is not None
    assert resp_with_recovery.recovery_progress.active_plans == 1
    assert resp_with_recovery.recovery_progress.overall_progress_pct == 33.3


def test_mastery_history_point_schema():
    from src.schemas.recovery import MasteryHistoryPoint
    now = datetime.now()
    point = MasteryHistoryPoint(
        average_score=65.0,
        attempt_count=2,
        severity="moderate",
        confidence=0.67,
        source="quiz",
        recorded_at=now,
    )
    assert point.average_score == 65.0
    assert point.attempt_count == 2
    assert point.severity == "moderate"
    assert point.source == "quiz"
    assert point.recorded_at == now


def test_mastery_history_point_empty_severity():
    from src.schemas.recovery import MasteryHistoryPoint
    now = datetime.now()
    point = MasteryHistoryPoint(
        average_score=35.0,
        attempt_count=1,
        severity="critical",
        confidence=0.33,
        source="task_completion",
        recorded_at=now,
    )
    assert point.severity == "critical"
    assert point.source == "task_completion"


def test_mastery_history_response_schema():
    from uuid import UUID

    from src.schemas.recovery import MasteryHistoryPoint, MasteryHistoryResponse
    now = datetime.now()
    point = MasteryHistoryPoint(
        average_score=45.0,
        attempt_count=1,
        severity="critical",
        confidence=0.33,
        source="quiz",
        recorded_at=now,
    )
    resp = MasteryHistoryResponse(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        topic="Cell Biology",
        history=[point],
    )
    assert resp.user_id == UUID("00000000-0000-0000-0000-000000000001")
    assert resp.topic == "Cell Biology"
    assert len(resp.history) == 1
    assert resp.history[0].average_score == 45.0


def test_mastery_history_response_empty():
    from uuid import UUID

    from src.schemas.recovery import MasteryHistoryResponse
    resp = MasteryHistoryResponse(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        topic="Genetics",
    )
    assert resp.history == []
    assert resp.topic == "Genetics"


def test_recovery_dashboard_response_has_weak_topics_history():
    from uuid import UUID

    from src.schemas.recovery import (
        MasteryHistoryPoint,
        MasteryHistoryResponse,
        WeakTopicDetail,
    )
    now = datetime.now()
    detail = WeakTopicDetail(
        topic="Cell Biology",
        average_score=45.0,
        severity="moderate",
    )
    history_point = MasteryHistoryPoint(
        average_score=45.0,
        attempt_count=1,
        severity="moderate",
        confidence=0.33,
        source="quiz",
        recorded_at=now,
    )
    history = MasteryHistoryResponse(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        topic="Cell Biology",
        history=[history_point],
    )
    assert history.topic == detail.topic
    assert history.history[0].average_score == detail.average_score


def test_recovery_notification_response_schema():
    from uuid import UUID

    from src.schemas.recovery import RecoveryNotificationResponse
    now = datetime.now()
    n = RecoveryNotificationResponse(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        topic="Cell Biology",
        event_type="mastery_improvement",
        message="Great progress in Cell Biology! Your mastery improved from 45% to 63%. Keep up the excellent work!",
        improvement_pct=18.0,
        old_value=45.0,
        new_value=63.0,
        is_read=False,
        created_at=now,
    )
    assert n.event_type == "mastery_improvement"
    assert n.improvement_pct == 18.0
    assert n.old_value == 45.0
    assert n.new_value == 63.0
    assert not n.is_read
    assert n.created_at == now


def test_recovery_notification_list_response_schema():
    from uuid import UUID

    from src.schemas.recovery import (
        RecoveryNotificationListResponse,
        RecoveryNotificationResponse,
    )
    now = datetime.now()
    n = RecoveryNotificationResponse(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        topic="Cell Biology",
        event_type="mastery_improvement",
        message="Great progress!",
        created_at=now,
    )
    resp = RecoveryNotificationListResponse(
        user_id=UUID("00000000-0000-0000-0000-000000000002"),
        notifications=[n],
        total_unread=1,
        total=1,
    )
    assert resp.total_unread == 1
    assert len(resp.notifications) == 1
    assert resp.notifications[0].topic == "Cell Biology"


def test_recovery_notification_list_empty():
    from uuid import UUID

    from src.schemas.recovery import RecoveryNotificationListResponse
    resp = RecoveryNotificationListResponse(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
    )
    assert resp.notifications == []
    assert resp.total_unread == 0
    assert resp.total == 0


def test_recovery_notification_different_event_types():
    from uuid import UUID

    from src.schemas.recovery import RecoveryNotificationResponse
    now = datetime.now()
    mastery = RecoveryNotificationResponse(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        topic="Genetics", event_type="mastery_improvement",
        message="Improved!",
        improvement_pct=12.0, old_value=50.0, new_value=62.0,
        created_at=now,
    )
    assert mastery.event_type == "mastery_improvement"
    assert mastery.improvement_pct == 12.0

    severity = RecoveryNotificationResponse(
        id=UUID("00000000-0000-0000-0000-000000000002"),
        topic="Photosynthesis", event_type="severity_upgrade",
        message="Severity improved!",
        created_at=now,
    )
    assert severity.event_type == "severity_upgrade"
    assert severity.improvement_pct is None

    plan = RecoveryNotificationResponse(
        id=UUID("00000000-0000-0000-0000-000000000003"),
        topic="Cell Division", event_type="plan_completed",
        message="Plan done!",
        improvement_pct=100.0,
        created_at=now,
    )
    assert plan.event_type == "plan_completed"
    assert plan.improvement_pct == 100.0


def test_dashboard_response_has_notification_fields():
    from uuid import UUID

    from src.schemas.recovery import (
        RecoveryDashboardResponse,
        RecoveryNotificationResponse,
    )
    now = datetime.now()
    n = RecoveryNotificationResponse(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        topic="Cell Biology", event_type="mastery_improvement",
        message="Great progress!", improvement_pct=15.0,
        created_at=now,
    )
    resp = RecoveryDashboardResponse(
        user_id=UUID("00000000-0000-0000-0000-000000000002"),
        unread_notifications=1,
        notifications=[n],
    )
    assert resp.unread_notifications == 1
    assert len(resp.notifications) == 1
    assert resp.notifications[0].improvement_pct == 15.0
