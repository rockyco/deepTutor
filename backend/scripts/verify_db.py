
import asyncio
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from app.db.database import async_session, init_db
from app.db.models import QuestionDB
from sqlalchemy import select

async def verify():
    await init_db()
    async with async_session() as session:
        result = await session.execute(select(QuestionDB))
        questions = result.scalars().all()
        print(f"Total Questions: {len(questions)}")
        for q in questions:
            print(f"- [{q.subject}] {q.question_type}: {q.get_content()['text'][:50]}...")

if __name__ == "__main__":
    asyncio.run(verify())
