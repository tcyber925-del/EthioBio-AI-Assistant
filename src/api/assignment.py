import structlog
from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.auth import get_current_user
from src.core.assignment import AssignmentService
from src.core.assignment.models import (
    Assignment,
    NewAssignment,
    NewSubmission,
    Submission,
    UpdateAssignment,
    UpdateSubmission,
)
from src.database.models import AssignmentStatus, User
from src.database.session import async_session_factory

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/assignments", tags=["Assignments"])

_service: AssignmentService | None = None


def _get_service() -> AssignmentService:
    global _service
    if _service is None:
        _service = AssignmentService(async_session_factory())
    return _service


@router.post("/", response_model=Assignment, status_code=201)
async def create_assignment(data: NewAssignment, current_user: User = Depends(get_current_user)):
    return await _get_service().create(data, str(current_user.id))


@router.get("/", response_model=list[Assignment])
async def list_assignments(
    workspace_id: str = Query(...),
    status: AssignmentStatus | None = Query(None),
):
    return await _get_service().list_for_workspace(workspace_id, status)


@router.get("/my", response_model=list[Assignment])
async def my_assignments(
    student_id: str = Query(...),
    status: AssignmentStatus | None = Query(None),
):
    return await _get_service().list_for_student(student_id, status)


@router.get("/{assignment_id}", response_model=Assignment)
async def get_assignment(assignment_id: str):
    result = await _get_service().get(assignment_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return result


@router.patch("/{assignment_id}", response_model=Assignment)
async def update_assignment(assignment_id: str, data: UpdateAssignment):
    result = await _get_service().update(assignment_id, data)
    if result is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return result


@router.post("/{assignment_id}/publish", response_model=Assignment)
async def publish_assignment(assignment_id: str):
    result = await _get_service().publish(assignment_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return result


@router.delete("/{assignment_id}", status_code=204)
async def delete_assignment(assignment_id: str):
    ok = await _get_service().soft_delete(assignment_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Assignment not found")


@router.post("/{assignment_id}/submissions", response_model=Submission, status_code=201)
async def submit_assignment(
    assignment_id: str,
    data: NewSubmission,
    current_user: User = Depends(get_current_user),
):
    result = await _get_service().submit(assignment_id, str(current_user.id), data)
    if result is None:
        raise HTTPException(status_code=404, detail="Assignment not found or max attempts exceeded")
    return result


@router.get("/submissions/my", response_model=list[Submission])
async def my_submissions(current_user: User = Depends(get_current_user)):
    return await _get_service().list_my_submissions(str(current_user.id))


@router.get("/{assignment_id}/submissions", response_model=list[Submission])
async def list_submissions(assignment_id: str):
    assignment = await _get_service().get(assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return await _get_service().list_submissions(assignment_id)


@router.get("/submissions/{submission_id}", response_model=Submission)
async def get_submission(submission_id: str):
    result = await _get_service().get_submission(submission_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    return result


@router.patch("/submissions/{submission_id}/review", response_model=Submission)
async def review_submission(submission_id: str, data: UpdateSubmission):
    result = await _get_service().review_submission(submission_id, data)
    if result is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    return result
