"""Question bank service for managing and retrieving questions."""

import json
import random
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import QuestionDB
from app.models.question import (
    Answer,
    AnswerCheck,
    AnswerResult,
    Question,
    QuestionContent,
    QuestionCreate,
    QuestionFormat,
    QuestionType,
    Subject,
    Hint,
)


class QuestionBankService:
    """Service for managing the question bank."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_question(self, question_id: UUID) -> Question | None:
        """Get a single question by ID."""
        result = await self.db.execute(
            select(QuestionDB).where(QuestionDB.id == str(question_id))
        )
        db_question = result.scalar_one_or_none()
        if not db_question:
            return None
        return self._db_to_model(db_question)

    async def get_questions(
        self,
        subject: Subject | None = None,
        question_type: QuestionType | None = None,
        difficulty: int | None = None,
        limit: int = 10,
        random_order: bool = True,
        exclude_ids: list[UUID] | None = None,
    ) -> list[Question]:
        """Get questions with optional filtering."""
        query = select(QuestionDB)

        if subject:
            query = query.where(QuestionDB.subject == subject.value)
        if question_type:
            query = query.where(QuestionDB.question_type == question_type.value)
        if difficulty:
            query = query.where(QuestionDB.difficulty == difficulty)
        if exclude_ids:
            exclude_str = [str(id) for id in exclude_ids]
            query = query.where(~QuestionDB.id.in_(exclude_str))

        result = await self.db.execute(query)
        db_questions = result.scalars().all()

        questions = [self._db_to_model(q) for q in db_questions]

        if random_order:
            random.shuffle(questions)

        return questions[:limit]

    async def create_question(self, question: QuestionCreate) -> Question:
        """Create a new question."""
        db_question = QuestionDB(
            subject=question.subject.value,
            question_type=question.question_type.value,
            format=question.format.value,
            difficulty=question.difficulty,
            content=json.dumps(question.content.model_dump()),
            answer=json.dumps(question.answer.model_dump()),
            explanation=question.explanation,
            hints=json.dumps([h.model_dump() for h in question.hints]),
            tags=json.dumps(question.tags),
            source=question.source,
        )
        self.db.add(db_question)
        await self.db.flush()
        return self._db_to_model(db_question)

    async def check_answer(self, answer_check: AnswerCheck) -> AnswerResult:
        """Check if a user's answer is correct."""
        question = await self.get_question(answer_check.question_id)
        if not question:
            raise ValueError(f"Question {answer_check.question_id} not found")

        is_correct = self._compare_answers(
            answer_check.user_answer,
            question.answer,
        )

        # Calculate score with hint penalty
        base_score = 1.0 if is_correct else 0.0
        hint_penalty = answer_check.hints_used * settings.hint_penalty
        score = max(0.0, base_score - hint_penalty)

        # Generate feedback
        if is_correct:
            feedback = "Excellent! That's correct."
            if answer_check.hints_used > 0:
                feedback += f" (Score reduced by {hint_penalty:.0%} for using {answer_check.hints_used} hint(s))"
        else:
            feedback = "Not quite right. Let's look at the explanation."

        return AnswerResult(
            is_correct=is_correct,
            correct_answer=question.answer.value,
            explanation=question.explanation,
            score=score,
            feedback=feedback,
        )

    async def get_hints(self, question_id: UUID, level: int = 1) -> list[Hint]:
        """Get hints up to a certain level for a question."""
        question = await self.get_question(question_id)
        if not question:
            return []
        return [h for h in question.hints if h.level <= level]

    async def get_question_count(
        self,
        subject: Subject | None = None,
        question_type: QuestionType | None = None,
    ) -> int:
        """Get count of questions matching criteria."""
        query = select(QuestionDB)
        if subject:
            query = query.where(QuestionDB.subject == subject.value)
        if question_type:
            query = query.where(QuestionDB.question_type == question_type.value)

        result = await self.db.execute(query)
        return len(result.scalars().all())

    async def load_questions_from_json(self, filepath: Path) -> int:
        """Load questions from a JSON file."""
        with open(filepath) as f:
            data = json.load(f)

        # Handle both {"questions": [...]} format and plain [...] format
        if isinstance(data, list):
            questions = data
        else:
            questions = data.get("questions", [])

        count = 0
        for q_data in questions:
            try:
                question = QuestionCreate(
                    subject=Subject(q_data["subject"]),
                    question_type=QuestionType(q_data["question_type"]),
                    format=QuestionFormat(q_data.get("format", "multiple_choice")),
                    difficulty=q_data.get("difficulty", 3),
                    content=QuestionContent(**q_data["content"]),
                    answer=Answer(**q_data["answer"]),
                    explanation=q_data["explanation"],
                    hints=[Hint(**h) for h in q_data.get("hints", [])],
                    tags=q_data.get("tags", []),
                    source=q_data.get("source"),
                )
                await self.create_question(question)
                count += 1
            except Exception as e:
                print(f"Error loading question: {e}")
                continue

        return count

    def _db_to_model(self, db_question: QuestionDB) -> Question:
        """Convert database model to Pydantic model."""
        content_data = json.loads(db_question.content)
        answer_data = json.loads(db_question.answer)
        hints_data = json.loads(db_question.hints)

        # Shuffle options to randomize answer position
        # The answer is matched by value, not position, so this is safe
        if "options" in content_data and content_data["options"]:
            options = content_data["options"].copy()
            random.shuffle(options)
            content_data["options"] = options

        return Question(
            id=UUID(db_question.id),
            subject=Subject(db_question.subject),
            question_type=QuestionType(db_question.question_type),
            format=QuestionFormat(db_question.format),
            difficulty=db_question.difficulty,
            content=QuestionContent(**content_data),
            answer=Answer(**answer_data),
            explanation=db_question.explanation,
            hints=[Hint(**h) for h in hints_data],
            tags=json.loads(db_question.tags),
            source=db_question.source,
            created_at=db_question.created_at,
        )

    def _compare_answers(
        self,
        user_answer: str | list | dict,
        correct: Answer,
    ) -> bool:
        """Compare user answer with correct answer."""
        user_str = str(user_answer).strip()
        correct_str = str(correct.value).strip()

        if not correct.case_sensitive:
            user_str = user_str.lower()
            correct_str = correct_str.lower()

        # Check main answer
        if user_str == correct_str:
            return True

        # Check variations
        if correct.accept_variations:
            for variation in correct.accept_variations:
                var_str = variation.strip()
                if not correct.case_sensitive:
                    var_str = var_str.lower()
                if user_str == var_str:
                    return True

        return False
