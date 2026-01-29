
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path.cwd() / "backend"))

from app.db.database import async_session
from app.db.models import QuestionDB
from sqlalchemy import delete

async def reset_nvr():
    async with async_session() as session:
        print("Deleting all Non-Verbal Reasoning questions...")
        statement = delete(QuestionDB).where(QuestionDB.subject == "non_verbal_reasoning")
        result = await session.execute(statement)
        await session.commit()
        print(f"Deleted {result.rowcount} NVR questions.")

if __name__ == "__main__":
    asyncio.run(reset_nvr())
