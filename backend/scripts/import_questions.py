#!/usr/bin/env python3
"""Import crawled questions into the database."""

import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import engine, init_db, async_session
from app.db.models import QuestionDB


async def import_questions(json_path: Path, skip_duplicates: bool = True) -> dict:
    """Import questions from a JSON file into the database.

    Args:
        json_path: Path to the JSON file with questions
        skip_duplicates: If True, skip questions with duplicate content

    Returns:
        Dictionary with import statistics
    """
    # Initialize database tables
    print("Initializing database tables...")
    await init_db()
    print("Database tables ready.")

    # Load questions from JSON
    print(f"Loading questions from {json_path}...")
    with open(json_path) as f:
        data = json.load(f)

    # Handle both formats: list of questions or dict with "questions" key
    if isinstance(data, list):
        questions = data
    else:
        questions = data.get("questions", [])
    print(f"Found {len(questions)} questions to import.")

    stats = {
        "total": len(questions),
        "imported": 0,
        "skipped_duplicate": 0,
        "skipped_error": 0,
    }

    # Get existing question content hashes for deduplication
    existing_hashes = set()
    if skip_duplicates:
        async with async_session() as session:
            from sqlalchemy import select
            result = await session.execute(select(QuestionDB.content))
            for row in result.scalars():
                # Simple hash of content for deduplication
                existing_hashes.add(hash(row))
        print(f"Found {len(existing_hashes)} existing questions in database.")

    # Import questions in batches
    batch_size = 100
    async with async_session() as session:
        for i, q in enumerate(questions):
            try:
                # Create content hash for deduplication
                content_json = json.dumps(q.get("content", {}), sort_keys=True)
                content_hash = hash(content_json)

                if skip_duplicates and content_hash in existing_hashes:
                    stats["skipped_duplicate"] += 1
                    continue

                # Create database record
                db_question = QuestionDB(
                    subject=q["subject"],
                    question_type=q["question_type"],
                    format=q.get("format", "multiple_choice"),
                    difficulty=q.get("difficulty", 3),
                    content=content_json,
                    answer=json.dumps(q.get("answer", {})),
                    explanation=q.get("explanation", ""),
                    hints=json.dumps(q.get("hints", [])),
                    tags=json.dumps(q.get("tags", [])),
                    source=q.get("source"),
                )

                session.add(db_question)
                existing_hashes.add(content_hash)
                stats["imported"] += 1

                # Commit in batches
                if stats["imported"] % batch_size == 0:
                    await session.commit()
                    print(f"  Imported {stats['imported']} questions...")

            except Exception as e:
                stats["skipped_error"] += 1
                print(f"  Error importing question {i}: {e}")

        # Final commit
        await session.commit()

    return stats


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Import crawled questions to database")
    parser.add_argument(
        "json_file",
        type=Path,
        help="Path to the JSON file with questions",
    )
    parser.add_argument(
        "--allow-duplicates",
        action="store_true",
        help="Allow duplicate questions",
    )

    args = parser.parse_args()

    if not args.json_file.exists():
        print(f"Error: File not found: {args.json_file}")
        sys.exit(1)

    stats = await import_questions(
        args.json_file,
        skip_duplicates=not args.allow_duplicates,
    )

    print("\n" + "=" * 50)
    print("Import Complete!")
    print("=" * 50)
    print(f"  Total questions in file: {stats['total']}")
    print(f"  Successfully imported:   {stats['imported']}")
    print(f"  Skipped (duplicate):     {stats['skipped_duplicate']}")
    print(f"  Skipped (error):         {stats['skipped_error']}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
