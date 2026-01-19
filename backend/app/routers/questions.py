"""Question API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.question import (
    AnswerCheck,
    AnswerResult,
    Hint,
    Question,
    QuestionCreate,
    QuestionType,
    Subject,
)
from app.services.question_bank import QuestionBankService

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.get("", response_model=list[Question])
async def get_questions(
    subject: Subject | None = None,
    question_type: QuestionType | None = None,
    difficulty: int | None = Query(None, ge=1, le=5),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get questions with optional filtering."""
    service = QuestionBankService(db)
    questions = await service.get_questions(
        subject=subject,
        question_type=question_type,
        difficulty=difficulty,
        limit=limit,
    )
    return questions


@router.get("/{question_id}", response_model=Question)
async def get_question(
    question_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single question by ID."""
    service = QuestionBankService(db)
    question = await service.get_question(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@router.post("", response_model=Question)
async def create_question(
    question: QuestionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new question."""
    service = QuestionBankService(db)
    return await service.create_question(question)


@router.post("/check", response_model=AnswerResult)
async def check_answer(
    answer_check: AnswerCheck,
    db: AsyncSession = Depends(get_db),
):
    """Check if an answer is correct and get explanation."""
    service = QuestionBankService(db)
    try:
        return await service.check_answer(answer_check)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{question_id}/hints", response_model=list[Hint])
async def get_hints(
    question_id: UUID,
    level: int = Query(1, ge=1, le=3),
    db: AsyncSession = Depends(get_db),
):
    """Get hints for a question up to a certain level."""
    service = QuestionBankService(db)
    hints = await service.get_hints(question_id, level)
    if not hints:
        raise HTTPException(status_code=404, detail="No hints available")
    return hints


@router.get("/count/{subject}", response_model=dict)
async def get_question_count(
    subject: Subject,
    question_type: QuestionType | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get count of questions for a subject."""
    service = QuestionBankService(db)
    count = await service.get_question_count(subject, question_type)
    return {"subject": subject.value, "count": count}
