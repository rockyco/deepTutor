"""Script to seed the database with sample questions."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.db import init_db, async_session
from app.services.question_bank import QuestionBankService


async def main():
    """Load sample questions into the database."""
    print("Initializing database...")
    await init_db()

    print("Loading questions from JSON files...")
    questions_dir = settings.questions_dir

    async with async_session() as db:
        service = QuestionBankService(db)

        total_loaded = 0
        for json_file in questions_dir.glob("*.json"):
            print(f"Loading {json_file.name}...")
            count = await service.load_questions_from_json(json_file)
            print(f"  Loaded {count} questions")
            total_loaded += count

        await db.commit()

    print(f"\nTotal questions loaded: {total_loaded}")

    # Print summary
    async with async_session() as db:
        service = QuestionBankService(db)
        from app.models.question import Subject

        print("\nQuestions by subject:")
        for subject in Subject:
            count = await service.get_question_count(subject)
            print(f"  {subject.value}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
