#!/usr/bin/env python3
"""Test a practice session with the imported questions."""

import asyncio
import json
import sys
from pathlib import Path
from uuid import uuid4

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import async_session, init_db
from app.db.models import UserDB, QuestionDB
from app.models.progress import PracticeSessionCreate
from app.models.question import Subject, QuestionType
from app.services.practice import PracticeService
from sqlalchemy import select, func


async def test_practice_session():
    """Test a full practice session flow."""
    print("=" * 60)
    print("Testing Practice Session with Crawled Questions")
    print("=" * 60)

    # Initialize database
    await init_db()

    async with async_session() as db:
        # Show available questions by subject
        print("\nAvailable questions by subject:")
        result = await db.execute(
            select(QuestionDB.subject, func.count())
            .group_by(QuestionDB.subject)
        )
        for subject, count in result:
            print(f"  {subject}: {count}")

        # Create or get a test user
        user_id = str(uuid4())
        user = UserDB(
            id=user_id,
            name="Test User",
            year_group=5,
        )
        db.add(user)
        await db.flush()
        print(f"\nCreated test user: {user_id}")

        # Test each subject
        subjects_to_test = [
            (Subject.MATHS, QuestionType.WORD_PROBLEMS, "Maths - Word Problems"),
            (Subject.ENGLISH, QuestionType.COMPREHENSION, "English - Comprehension"),
            (Subject.VERBAL_REASONING, QuestionType.VR_ANAGRAMS, "VR - Anagrams"),
        ]

        for subject, question_type, label in subjects_to_test:
            print(f"\n{'='*60}")
            print(f"Testing: {label}")
            print("=" * 60)

            try:
                # Create practice service
                service = PracticeService(db)

                # Start a session with 3 questions
                config = PracticeSessionCreate(
                    subject=subject,
                    question_type=question_type,
                    num_questions=3,
                    is_timed=False,
                )

                session = await service.start_session(uuid4().bytes[:16].hex(), config)
                print(f"\nStarted session: {session.id}")
                print(f"  Questions: {len(session.question_ids)}")

                # Get and display each question
                for i, qid in enumerate(session.question_ids, 1):
                    from app.services.question_bank import QuestionBankService
                    qbank = QuestionBankService(db)
                    question = await qbank.get_question(qid)

                    if question:
                        print(f"\n  Question {i}:")
                        print(f"    Type: {question.question_type.value}")
                        print(f"    Difficulty: {question.difficulty}")

                        # Truncate long text
                        text = question.content.text or ""
                        if len(text) > 100:
                            text = text[:100] + "..."
                        print(f"    Text: {text}")

                        options = question.content.options or []
                        if options:
                            print(f"    Options: {options[:4]}")

                        # Show correct answer
                        answer = question.answer.value
                        print(f"    Correct Answer: {answer}")

                        # Submit the correct answer
                        await service.submit_answer(
                            session_id=session.id,
                            question_id=qid,
                            user_answer=answer,
                            time_taken_seconds=30,
                            hints_used=0,
                        )

                # Complete session
                result = await service.complete_session(session.id)
                print(f"\n  Session Results:")
                print(f"    Total: {result.total_questions}")
                print(f"    Correct: {result.correct_answers}")
                print(f"    Accuracy: {result.accuracy:.1%}")
                print(f"    Score: {result.total_score:.1f}")

            except ValueError as e:
                print(f"  Error: {e}")
            except Exception as e:
                print(f"  Unexpected error: {type(e).__name__}: {e}")

        # Commit changes
        await db.commit()

    print("\n" + "=" * 60)
    print("Practice session test complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_practice_session())
