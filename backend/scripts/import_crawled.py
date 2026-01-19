#!/usr/bin/env python3
"""Import crawled questions from JSON files to the database."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import init_db, async_session
from app.services.question_bank import QuestionBankService
from app.models.question import Subject


async def main():
    """Import crawled questions to database."""
    print("Initializing database...")
    await init_db()

    crawled_dir = Path(__file__).parent.parent / "data" / "crawled"

    if not crawled_dir.exists():
        print(f"Error: {crawled_dir} does not exist")
        return

    async with async_session() as db:
        service = QuestionBankService(db)

        # Get current counts
        print("\nCurrent question counts:")
        for subject in Subject:
            count = await service.get_question_count(subject)
            print(f"  {subject.value}: {count}")

        total_imported = 0

        for json_file in sorted(crawled_dir.glob("*.json")):
            print(f"\nImporting {json_file.name}...")
            try:
                count = await service.load_questions_from_json(json_file)
                print(f"  Imported {count} questions")
                total_imported += count
            except Exception as e:
                print(f"  Error: {e}")

        await db.commit()
        print(f"\n{'='*50}")
        print(f"Total imported: {total_imported}")

        # Get new counts
        print("\nNew question counts:")
        for subject in Subject:
            count = await service.get_question_count(subject)
            print(f"  {subject.value}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
