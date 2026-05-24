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
