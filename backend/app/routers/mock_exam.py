"""Mock exam API endpoints for GL Assessment format exams."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.mock_exam import (
    MockExamAnswer,
    MockExamResult,
    MockExamSession,
)
from app.services.mock_exam import MockExamService

router = APIRouter(prefix="/api/mock-exam", tags=["mock-exam"])


class StartExamRequest(BaseModel):
    user_id: str
    exam_number: int = 1


@router.post("/start", response_model=MockExamSession)
async def start_exam(
    request: StartExamRequest,
    db: AsyncSession = Depends(get_db),
):
    """Start a new mock exam session.

    Creates a 2-paper exam with 4 timed sections per paper,
    following the Trafford Grammar School GL Assessment format.
    """
    service = MockExamService(db)
    session = await service.create_exam(
        user_id=request.user_id,
        exam_number=request.exam_number,
    )
    return session


@router.get("/{exam_id}", response_model=MockExamSession)
async def get_exam(
    exam_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get an existing mock exam session."""
    service = MockExamService(db)
    session = await service.get_exam(exam_id)
    if not session:
        raise HTTPException(status_code=404, detail="Exam not found")
    return session


@router.get("/{exam_id}/paper/{paper_num}/section/{section_index}")
async def get_section_questions(
    exam_id: str,
    paper_num: int,
    section_index: int,
    db: AsyncSession = Depends(get_db),
):
    """Get full question data for a specific section of a paper."""
    service = MockExamService(db)
    questions = await service.get_section_questions(exam_id, paper_num, section_index)
    if not questions:
        raise HTTPException(status_code=404, detail="Section not found or empty")
    return questions


@router.post("/{exam_id}/answer")
async def submit_answer(
    exam_id: str,
    answer: MockExamAnswer,
    db: AsyncSession = Depends(get_db),
):
    """Submit an answer for a question in the exam."""
    service = MockExamService(db)
    result = await service.submit_answer(exam_id, answer)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{exam_id}/complete", response_model=MockExamResult)
async def complete_exam(
    exam_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Complete the exam and get results."""
    service = MockExamService(db)
    result = await service.complete_exam(exam_id)
    if not result:
        raise HTTPException(status_code=404, detail="Exam not found")
    return result
