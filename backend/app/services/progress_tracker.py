"""Progress tracking service."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProgressDB, UserDB, PracticeSessionDB
from app.models.progress import Progress, ProgressSummary
from app.models.question import QuestionType, Subject


class ProgressTrackerService:
    """Service for tracking user progress."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_progress(
        self,
        user_id: UUID,
        subject: Subject,
        question_type: QuestionType,
    ) -> Progress:
        """Get or create progress record for a user/subject/type combination."""
        result = await self.db.execute(
            select(ProgressDB).where(
                ProgressDB.user_id == str(user_id),
                ProgressDB.subject == subject.value,
                ProgressDB.question_type == question_type.value,
            )
        )
        db_progress = result.scalar_one_or_none()

        if db_progress:
            return self._db_to_model(db_progress)

        # Create new progress record
        db_progress = ProgressDB(
            user_id=str(user_id),
            subject=subject.value,
            question_type=question_type.value,
        )
        self.db.add(db_progress)
        await self.db.flush()

        return self._db_to_model(db_progress)

    async def update_progress(
        self,
        user_id: UUID,
        subject: Subject,
        question_type: QuestionType,
        is_correct: bool,
    ) -> Progress:
        """Update progress after answering a question."""
        progress = await self.get_or_create_progress(user_id, subject, question_type)

        result = await self.db.execute(
            select(ProgressDB).where(ProgressDB.id == str(progress.id))
        )
        db_progress = result.scalar_one()

        db_progress.total_attempted += 1
        if is_correct:
            db_progress.total_correct += 1
            db_progress.streak += 1
        else:
            db_progress.streak = 0

        db_progress.last_practiced = datetime.utcnow()

        # Update mastery score (weighted average of recent performance)
        accuracy = db_progress.total_correct / db_progress.total_attempted
        db_progress.mastery_score = accuracy

        # Adjust difficulty level based on performance
        if db_progress.total_attempted >= 5:
            if accuracy >= 0.9 and db_progress.current_level < 5:
                db_progress.current_level += 1
            elif accuracy < 0.5 and db_progress.current_level > 1:
                db_progress.current_level -= 1

        await self.db.flush()
        return self._db_to_model(db_progress)

    async def get_progress_summary(self, user_id: UUID) -> ProgressSummary:
        """Get complete progress summary for a user."""
        # Get all progress records
        result = await self.db.execute(
            select(ProgressDB).where(ProgressDB.user_id == str(user_id))
        )
        progress_records = result.scalars().all()

        # Get user stats
        user_result = await self.db.execute(
            select(UserDB).where(UserDB.id == str(user_id))
        )
        user = user_result.scalar_one_or_none()

        # Aggregate by subject
        subjects: dict[str, dict] = {}
        for p in progress_records:
            if p.subject not in subjects:
                subjects[p.subject] = {
                    "mastery": 0.0,
                    "total_attempted": 0,
                    "total_correct": 0,
                    "types": {},
                }
            subjects[p.subject]["total_attempted"] += p.total_attempted
            subjects[p.subject]["total_correct"] += p.total_correct
            subjects[p.subject]["types"][p.question_type] = {
                "mastery": p.mastery_score,
                "attempted": p.total_attempted,
                "correct": p.total_correct,
                "level": p.current_level,
            }

        # Calculate subject-level mastery
        for subject_data in subjects.values():
            if subject_data["total_attempted"] > 0:
                subject_data["mastery"] = (
                    subject_data["total_correct"] / subject_data["total_attempted"]
                )
                subject_data["accuracy"] = subject_data["mastery"]

        # Identify weak and strong areas
        weak_areas = []
        strong_areas = []
        for p in progress_records:
            if p.total_attempted >= 3:  # Minimum attempts for classification
                accuracy = p.total_correct / p.total_attempted
                area_info = {
                    "subject": p.subject,
                    "type": p.question_type,
                    "accuracy": accuracy,
                    "attempted": p.total_attempted,
                }
                if accuracy < 0.5:
                    weak_areas.append(area_info)
                elif accuracy >= 0.8:
                    strong_areas.append(area_info)

        # Sort by accuracy
        weak_areas.sort(key=lambda x: x["accuracy"])
        strong_areas.sort(key=lambda x: x["accuracy"], reverse=True)

        # Get recent activity
        sessions_result = await self.db.execute(
            select(PracticeSessionDB)
            .where(PracticeSessionDB.user_id == str(user_id))
            .order_by(PracticeSessionDB.started_at.desc())
            .limit(5)
        )
        recent_sessions = sessions_result.scalars().all()
        recent_activity = [
            {
                "date": s.started_at.isoformat(),
                "subject": s.subject,
                "questions": s.total_questions,
                "correct": s.correct_answers,
            }
            for s in recent_sessions
        ]

        # Generate recommendations
        recommended_next = []
        for area in weak_areas[:3]:
            recommended_next.append({
                "subject": area["subject"],
                "type": area["type"],
                "reason": f"Low accuracy ({area['accuracy']:.0%})",
            })

        # Calculate overall mastery
        total_attempted = sum(p.total_attempted for p in progress_records)
        total_correct = sum(p.total_correct for p in progress_records)
        overall_mastery = total_correct / total_attempted if total_attempted > 0 else 0.0

        return ProgressSummary(
            user_id=user_id,
            overall_mastery=overall_mastery,
            subjects=subjects,
            weak_areas=weak_areas,
            strong_areas=strong_areas,
            recent_activity=recent_activity,
            recommended_next=recommended_next,
        )

    async def get_weak_areas(self, user_id: UUID, limit: int = 5) -> list[dict]:
        """Get the user's weakest areas that need practice."""
        summary = await self.get_progress_summary(user_id)
        return summary.weak_areas[:limit]

    async def get_recommended_difficulty(
        self,
        user_id: UUID,
        subject: Subject,
        question_type: QuestionType,
    ) -> int:
        """Get recommended difficulty level for a user."""
        progress = await self.get_or_create_progress(user_id, subject, question_type)
        return progress.current_level

    def _db_to_model(self, db_progress: ProgressDB) -> Progress:
        """Convert database model to Pydantic model."""
        return Progress(
            id=UUID(db_progress.id),
            user_id=UUID(db_progress.user_id),
            subject=Subject(db_progress.subject),
            question_type=QuestionType(db_progress.question_type),
            total_attempted=db_progress.total_attempted,
            total_correct=db_progress.total_correct,
            current_level=db_progress.current_level,
            mastery_score=db_progress.mastery_score,
            last_practiced=db_progress.last_practiced,
            streak=db_progress.streak,
        )
