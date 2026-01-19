#!/usr/bin/env python3
"""Show sample questions from the database."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import async_session, init_db
from app.db.models import QuestionDB
from sqlalchemy import select


async def main():
    await init_db()

    async with async_session() as db:
        # Sample from different categories
        categories = [
            ("vr_anagrams", "VR Anagrams"),
            ("word_problems", "Maths Word Problems"),
            ("comprehension", "English Comprehension"),
        ]

        for qtype, label in categories:
            print(f"\n{'='*60}")
            print(f"{label}")
            print("=" * 60)

            result = await db.execute(
                select(QuestionDB)
                .where(QuestionDB.question_type == qtype)
                .where(QuestionDB.source.like("crawled:%"))
                .limit(2)
            )
            questions = result.scalars().all()

            for i, q in enumerate(questions, 1):
                content = json.loads(q.content)
                answer = json.loads(q.answer)

                print(f"\nQuestion {i}:")
                text = content.get("text", "")
                if len(text) > 100:
                    text = text[:100] + "..."
                print(f"  Text: {text}")

                opts = content.get("options", [])
                if opts:
                    print(f"  Options: {opts[:4]}")

                print(f"  Answer: {answer.get('value')}")
                print(f"  Source: {q.source}")


if __name__ == "__main__":
    asyncio.run(main())
