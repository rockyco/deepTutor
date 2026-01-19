#!/usr/bin/env python3
"""Startup script to initialize database and seed questions."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import async_session, init_db
from app.db.models import QuestionDB
from sqlalchemy import select, func


async def seed_questions():
    """Seed database with questions from JSON files."""
    async with async_session() as session:
        # Check if questions already exist
        count = await session.scalar(select(func.count()).select_from(QuestionDB))
        if count and count > 0:
            print(f"Database already has {count} questions. Skipping seed.")
            return

        print("Seeding database with questions...")

        # Load questions from JSON files
        questions_dir = Path(__file__).parent.parent / "data" / "questions"
        total_imported = 0

        for json_file in questions_dir.glob("*.json"):
            print(f"Loading {json_file.name}...")
            with open(json_file) as f:
                data = json.load(f)

            questions = data if isinstance(data, list) else data.get("questions", [])

            for q in questions:
                try:
                    db_question = QuestionDB(
                        subject=q["subject"],
                        question_type=q["question_type"],
                        format=q.get("format", "multiple_choice"),
                        difficulty=q.get("difficulty", 3),
                        content=json.dumps(q.get("content", {})),
                        answer=json.dumps(q.get("answer", {})),
                        explanation=q.get("explanation", ""),
                        hints=json.dumps(q.get("hints", [])),
                        tags=json.dumps(q.get("tags", [])),
                        source=q.get("source"),
                    )
                    session.add(db_question)
                    total_imported += 1
                except Exception as e:
                    print(f"  Error importing question: {e}")

            await session.commit()

        print(f"Imported {total_imported} questions.")


async def main():
    """Initialize database and seed questions."""
    print("Initializing database...")
    await init_db()
    print("Database initialized.")

    await seed_questions()
    print("Startup complete.")


if __name__ == "__main__":
    asyncio.run(main())
