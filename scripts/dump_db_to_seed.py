
import asyncio
import json
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.append(str(Path.cwd() / "backend"))

from app.db.database import async_session
from app.db.models import QuestionDB
from sqlalchemy import select

async def dump_db():
    output_file = Path("backend/data/questions/deployment_dump.json")
    
    async with async_session() as session:
        result = await session.execute(select(QuestionDB))
        questions = result.scalars().all()
        
    export_data = []
    for q in questions:
        # Reconstruct Pydantic-like dict
        q_dict = {
            "subject": q.subject,
            "question_type": q.question_type,
            "format": q.format,
            "difficulty": q.difficulty,
            "content": json.loads(q.content),
            "answer": json.loads(q.answer),
            "explanation": q.explanation,
            "hints": json.loads(q.hints),
            "tags": json.loads(q.tags),
            "source": q.source
        }
        export_data.append(q_dict)
        
    with open(output_file, "w") as f:
        json.dump(export_data, f, indent=2)
        
    print(f"Dumped {len(export_data)} questions to {output_file}")

if __name__ == "__main__":
    asyncio.run(dump_db())
