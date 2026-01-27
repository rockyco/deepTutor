"""Update NVR questions in database with extracted granular images."""
import asyncio
import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.append(str(Path(__file__).parent.parent))
from app.db.database import async_session, init_db
from app.db.models import QuestionDB
from sqlalchemy import select, delete

SCRIPT_DIR = Path(__file__).parent
METADATA_FILE = SCRIPT_DIR.parent / "data" / "images" / "granular" / "nvr_metadata.json"

async def update_nvr_questions():
    await init_db()
    
    # Load metadata
    with open(METADATA_FILE) as f:
        questions_data = json.load(f)
    
    print(f"Loaded {len(questions_data)} questions from metadata")
    
    async with async_session() as session:
        # Delete existing NVR questions
        stmt = delete(QuestionDB).where(QuestionDB.subject == 'non_verbal_reasoning')
        result = await session.execute(stmt)
        print(f"Deleted {result.rowcount} existing NVR questions")
        
        # Insert new questions
        for q_data in questions_data:
            content = {
                "text": q_data["text"],
                "image_url": q_data["main_image"],
                "option_images": q_data["option_images"],
                "options": q_data["options"]
            }
            
            db_question = QuestionDB(
                id=str(uuid4()),
                subject="non_verbal_reasoning",
                question_type="nvr_visual",
                format="multiple_choice",
                difficulty=3,
                content=json.dumps(content),
                answer=json.dumps({"value": q_data.get("answer", "A")}),
                explanation="This is a Non-Verbal Reasoning question from CGP 11+ sample test.",
                hints=json.dumps([]),
                tags=json.dumps(["nvr", "visual", "cgp"]),
                source="CGP 11+ Free Sample"
            )
            session.add(db_question)
            print(f"Added Q{q_data['question_num']}: {q_data['text'][:50]}...")
        
        await session.commit()
        print(f"\n=== Successfully added {len(questions_data)} NVR questions ===")

if __name__ == "__main__":
    asyncio.run(update_nvr_questions())
