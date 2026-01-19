"""Practice session API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.progress import (
    PracticeSession,
    PracticeSessionCreate,
    PracticeSessionResult,
    UserAnswer,
)
from app.models.question import Question
from app.services.practice import PracticeService
from app.services.question_bank import QuestionBankService

router = APIRouter(prefix="/api/practice", tags=["practice"])


class StartSessionRequest(BaseModel):
    """Request body for starting a practice session."""

    user_id: UUID
    config: PracticeSessionCreate


class SubmitAnswerRequest(BaseModel):
    """Request body for submitting an answer."""

    question_id: UUID
    user_answer: str | list[str] | dict[str, str]
    time_taken_seconds: int
    hints_used: int = 0


@router.post("/start", response_model=PracticeSession)
async def start_session(
    request: StartSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Start a new practice session."""
    service = PracticeService(db)
    try:
        session = await service.start_session(request.user_id, request.config)
        return session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}", response_model=PracticeSession)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a practice session by ID."""
    service = PracticeService(db)
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/{session_id}/next", response_model=Question | None)
async def get_next_question(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the next unanswered question in a session."""
    practice_service = PracticeService(db)
    question_service = QuestionBankService(db)

    next_id = await practice_service.get_next_question(session_id)
    if not next_id:
        return None

    question = await question_service.get_question(next_id)
    return question


@router.post("/{session_id}/answer", response_model=UserAnswer)
async def submit_answer(
    session_id: UUID,
    request: SubmitAnswerRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit an answer for a question in a session."""
    service = PracticeService(db)

    # Verify session exists
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify question is in session
    if request.question_id not in session.question_ids:
        raise HTTPException(status_code=400, detail="Question not in this session")

    # Check if already answered
    answered_ids = {a.question_id for a in session.answers}
    if request.question_id in answered_ids:
        raise HTTPException(status_code=400, detail="Question already answered")

    answer = await service.submit_answer(
        session_id=session_id,
        question_id=request.question_id,
        user_answer=request.user_answer,
        time_taken_seconds=request.time_taken_seconds,
        hints_used=request.hints_used,
    )
    return answer


@router.post("/{session_id}/complete", response_model=PracticeSessionResult)
async def complete_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Complete a practice session and get results."""
    service = PracticeService(db)
    try:
        result = await service.complete_session(session_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{session_id}/results", response_model=PracticeSessionResult)
async def get_session_results(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get results for a completed session."""
    service = PracticeService(db)

    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.completed_at:
        raise HTTPException(status_code=400, detail="Session not yet completed")

    # Re-calculate results
    result = await service.complete_session(session_id)
    return result
