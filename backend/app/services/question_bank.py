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

        questions = []
        for q in db_questions:
            try:
                model = self._db_to_model(q)
                questions.append(model)
            except Exception as e:
                # Log error but continue
                print(f"Error converting question {q.id}: {e}")
                continue

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
            question.content
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
            # Return the actual value text if possible, otherwise the letter
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
        try:
            content_data = json.loads(db_question.content)
            answer_data = json.loads(db_question.answer)
            hints_data = json.loads(db_question.hints) if db_question.hints else []
            tags_data = json.loads(db_question.tags) if db_question.tags else []

            if "options" in content_data and content_data["options"]:
                options = content_data["options"]
                # random.shuffle(options) - REMOVED: Shuffling breaks answer key (e.g. Answer 'A' must point to first option)
                content_data["options"] = options

            return Question(
                id=UUID(db_question.id),
                subject=Subject(db_question.subject) if db_question.subject else Subject.MATHS, # Fallback
                question_type=QuestionType(db_question.question_type) if db_question.question_type else QuestionType.ARITHMETIC, # Fallback
                format=QuestionFormat(db_question.format),
                difficulty=db_question.difficulty,
                content=QuestionContent(**content_data),
                answer=Answer(**answer_data),
                explanation=db_question.explanation or "",
                hints=[Hint(**h) for h in hints_data],
                tags=tags_data,
                source=db_question.source,
                created_at=db_question.created_at,
            )
        except Exception as e:
            # We raise so that the caller 'get_questions' catches it (or crashes if single get)
            # ideally get_questions should catch this
            raise ValueError(f"Data corruption in question {db_question.id}: {e}")

    def _compare_answers(
        self,
        user_answer: str | list | dict,
        correct: Answer,
        content: QuestionContent | None = None,
    ) -> bool:
        """Compare user answer with correct answer using robust set logic and text-to-letter resolution."""
        
        def normalize_to_set(val, known_options: list[str] | None = None) -> set[str]:
            """Helper to convert any input to a set of normalized strings."""
            if isinstance(val, (list, tuple)):
                return set(str(v).strip().upper() for v in val)
            
            if isinstance(val, str):
                val_clean = val.strip().upper()
                
                # OPTIMIZATION: If this string matches a known option exactly, don't split it!
                # (Fixes answers like "A triangle, base 10 m, height 4 m.")
                if known_options:
                     norm_options = [o.strip().upper() for o in known_options]
                     if val_clean in norm_options:
                         return {val_clean}

                # Handle comma-separated like "A, B"
                parts = val.split(',')
                return set(p.strip().upper() for p in parts if p.strip())
                
            return set([str(val).strip().upper()])

        # Get options for smart normalization
        current_options = content.options if content and content.options else None

        # Normalize both inputs
        user_set = normalize_to_set(user_answer, current_options)
        correct_set = normalize_to_set(correct.value, current_options)
        
        # 1. Direct Match (Letter vs Letter OR Text vs Text if backend stored text)
        if user_set == correct_set:
            return True

        # 2. Text-to-Letter Resolution (User sent "Discredit", Correct is "C")
        if content and content.options:
            # Map user text to potential letters
            resolved_letters = set()
            options = [opt.strip().upper() for opt in content.options]
            
            for u_item in user_set:
                # If user sent "A", keep "A". If "Discredit", find index
                if u_item in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]:
                     resolved_letters.add(u_item)
                     continue
                
                # Try finding text match in options
                # Exact match
                try:
                    idx = options.index(u_item)
                    resolved_letters.add(chr(65 + idx)) # 0->A
                except ValueError:
                    # Fuzzy match fallback could go here
                    pass
            
            if resolved_letters and resolved_letters == correct_set:
                return True

        # 3. Check Variations
        if correct.accept_variations:
            for variation in correct.accept_variations:
                if user_set == normalize_to_set(variation):
                    return True

        return False
