"""Practice session service."""

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PracticeSessionDB, UserAnswerDB, UserDB
from app.models.progress import (
    PracticeSession,
    PracticeSessionCreate,
    PracticeSessionResult,
    UserAnswer,
)
from app.models.question import QuestionType, Subject

from .question_bank import QuestionBankService


class PracticeService:
    """Service for managing practice sessions."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.question_bank = QuestionBankService(db)

    async def start_session(
        self,
        user_id: UUID,
        config: PracticeSessionCreate,
    ) -> PracticeSession:
        """Start a new practice session."""
        # Get questions for the session
        questions = await self.question_bank.get_questions(
            subject=config.subject,
            question_type=config.question_type,
            difficulty=config.difficulty,
            limit=config.num_questions,
            random_order=True,
        )

        if not questions:
            raise ValueError("No questions available matching criteria")

        question_ids = [str(q.id) for q in questions]

        # Create database record
        db_session = PracticeSessionDB(
            user_id=str(user_id),
            subject=config.subject.value if config.subject else None,
            question_type=config.question_type.value if config.question_type else None,
            is_timed=config.is_timed,
            time_limit_minutes=config.time_limit_minutes,
            question_ids=json.dumps(question_ids),
            total_questions=len(question_ids),
        )
        self.db.add(db_session)
        await self.db.flush()

        return PracticeSession(
            id=UUID(db_session.id),
            user_id=user_id,
            subject=config.subject,
            question_type=config.question_type,
            is_timed=config.is_timed,
            time_limit_minutes=config.time_limit_minutes,
            question_ids=[UUID(qid) for qid in question_ids],
        )

    async def get_session(self, session_id: UUID) -> PracticeSession | None:
        """Get a practice session by ID."""
        result = await self.db.execute(
            select(PracticeSessionDB).where(PracticeSessionDB.id == str(session_id))
        )
        db_session = result.scalar_one_or_none()
        if not db_session:
            return None

        # Get answers
        answers_result = await self.db.execute(
            select(UserAnswerDB).where(UserAnswerDB.session_id == str(session_id))
        )
        db_answers = answers_result.scalars().all()

        answers = [
            UserAnswer(
                id=UUID(a.id),
                session_id=UUID(a.session_id),
                question_id=UUID(a.question_id),
                user_answer=json.loads(a.user_answer),
                is_correct=a.is_correct,
                time_taken_seconds=a.time_taken_seconds,
                hints_used=a.hints_used,
                score=a.score,
                created_at=a.created_at,
            )
            for a in db_answers
        ]

        return PracticeSession(
            id=UUID(db_session.id),
            user_id=UUID(db_session.user_id),
            subject=Subject(db_session.subject) if db_session.subject else None,
            question_type=QuestionType(db_session.question_type) if db_session.question_type else None,
            is_timed=db_session.is_timed,
            time_limit_minutes=db_session.time_limit_minutes,
            started_at=db_session.started_at,
            completed_at=db_session.completed_at,
            question_ids=[UUID(qid) for qid in json.loads(db_session.question_ids)],
            answers=answers,
        )

    async def submit_answer(
        self,
        session_id: UUID,
        question_id: UUID,
        user_answer: str | list | dict,
        time_taken_seconds: int,
        hints_used: int = 0,
    ) -> UserAnswer:
        """Submit an answer for a question in a session."""
        # Check the answer
        from app.models.question import AnswerCheck

        answer_check = AnswerCheck(
            question_id=question_id,
            user_answer=user_answer,
            time_taken_seconds=time_taken_seconds,
            hints_used=hints_used,
        )
        result = await self.question_bank.check_answer(answer_check)

        # Create answer record
        db_answer = UserAnswerDB(
            session_id=str(session_id),
            question_id=str(question_id),
            user_answer=json.dumps(user_answer),
            is_correct=result.is_correct,
            time_taken_seconds=time_taken_seconds,
            hints_used=hints_used,
            score=result.score,
        )
        self.db.add(db_answer)

        # Update session stats
        session_result = await self.db.execute(
            select(PracticeSessionDB).where(PracticeSessionDB.id == str(session_id))
        )
        db_session = session_result.scalar_one()
        if result.is_correct:
            db_session.correct_answers += 1
        db_session.total_score += result.score

        await self.db.flush()

        return UserAnswer(
            id=UUID(db_answer.id),
            session_id=session_id,
            question_id=question_id,
            user_answer=user_answer,
            is_correct=result.is_correct,
            time_taken_seconds=time_taken_seconds,
            hints_used=hints_used,
            score=result.score,
        )

    async def complete_session(self, session_id: UUID) -> PracticeSessionResult:
        """Complete a practice session and generate results."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Update completion time
        result = await self.db.execute(
            select(PracticeSessionDB).where(PracticeSessionDB.id == str(session_id))
        )
        db_session = result.scalar_one()
        db_session.completed_at = datetime.utcnow()

        # Update user stats
        user_result = await self.db.execute(
            select(UserDB).where(UserDB.id == db_session.user_id)
        )
        user = user_result.scalar_one_or_none()
        if user:
            user.total_questions_attempted += session.total_questions
            user.total_correct += session.correct_answers
            user.last_active = datetime.utcnow()

            # Calculate time
            if session.started_at and db_session.completed_at:
                time_diff = (db_session.completed_at - session.started_at).total_seconds() / 60
                user.total_practice_time_minutes += int(time_diff)

        await self.db.flush()

        # Calculate results by question type
        questions_by_type: dict[str, dict[str, int]] = {}
        for answer in session.answers:
            question = await self.question_bank.get_question(answer.question_id)
            if question:
                qtype = question.question_type.value
                if qtype not in questions_by_type:
                    questions_by_type[qtype] = {"attempted": 0, "correct": 0}
                questions_by_type[qtype]["attempted"] += 1
                if answer.is_correct:
                    questions_by_type[qtype]["correct"] += 1

        # Identify strengths and weaknesses
        strengths = []
        areas_to_improve = []
        for qtype, stats in questions_by_type.items():
            if stats["attempted"] > 0:
                accuracy = stats["correct"] / stats["attempted"]
                if accuracy >= 0.8:
                    strengths.append(qtype)
                elif accuracy < 0.5:
                    areas_to_improve.append(qtype)

        time_taken = 0.0
        if session.started_at and db_session.completed_at:
            time_taken = (db_session.completed_at - session.started_at).total_seconds() / 60

        return PracticeSessionResult(
            session_id=session_id,
            subject=session.subject,
            total_questions=session.total_questions,
            correct_answers=session.correct_answers,
            accuracy=session.accuracy,
            total_score=session.total_score,
            time_taken_minutes=time_taken,
            questions_by_type=questions_by_type,
            strengths=strengths,
            areas_to_improve=areas_to_improve,
        )

    async def get_next_question(self, session_id: UUID) -> UUID | None:
        """Get the next unanswered question in a session."""
        session = await self.get_session(session_id)
        if not session:
            return None

        answered_ids = {a.question_id for a in session.answers}
        for qid in session.question_ids:
            if qid not in answered_ids:
                return qid

        return None  # All questions answered
