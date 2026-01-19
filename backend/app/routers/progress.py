"""Progress tracking API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.progress import Progress, ProgressSummary
from app.models.question import QuestionType, Subject
from app.services.progress_tracker import ProgressTrackerService

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("/{user_id}", response_model=ProgressSummary)
async def get_progress_summary(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get complete progress summary for a user."""
    service = ProgressTrackerService(db)
    return await service.get_progress_summary(user_id)


@router.get("/{user_id}/subject/{subject}", response_model=list[Progress])
async def get_subject_progress(
    user_id: UUID,
    subject: Subject,
    db: AsyncSession = Depends(get_db),
):
    """Get progress for all question types in a subject."""
    service = ProgressTrackerService(db)
    summary = await service.get_progress_summary(user_id)

    # Filter to requested subject
    progress_list = []
    if subject.value in summary.subjects:
        subject_data = summary.subjects[subject.value]
        for qtype, type_data in subject_data.get("types", {}).items():
            progress = await service.get_or_create_progress(
                user_id, subject, QuestionType(qtype)
            )
            progress_list.append(progress)

    return progress_list


@router.get("/{user_id}/weaknesses", response_model=list[dict])
async def get_weak_areas(
    user_id: UUID,
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Get the user's weakest areas that need practice."""
    service = ProgressTrackerService(db)
    return await service.get_weak_areas(user_id, limit)


@router.get("/{user_id}/recommendations", response_model=list[dict])
async def get_recommendations(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get recommended practice areas for a user."""
    service = ProgressTrackerService(db)
    summary = await service.get_progress_summary(user_id)
    return summary.recommended_next


@router.get("/{user_id}/difficulty", response_model=dict)
async def get_recommended_difficulty(
    user_id: UUID,
    subject: Subject,
    question_type: QuestionType,
    db: AsyncSession = Depends(get_db),
):
    """Get recommended difficulty level for a user/subject/type combination."""
    service = ProgressTrackerService(db)
    difficulty = await service.get_recommended_difficulty(user_id, subject, question_type)
    return {
        "subject": subject.value,
        "question_type": question_type.value,
        "recommended_difficulty": difficulty,
    }
