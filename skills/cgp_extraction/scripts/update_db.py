
import asyncio
import json
import sys
from pathlib import Path
from uuid import uuid4

# Add backend to path for imports
sys.path.append(str(Path.cwd() / "backend"))

from app.db.database import async_session, init_db
from app.db.models import QuestionDB
from sqlalchemy import select, delete


import asyncio
import json
import sys
import glob
from pathlib import Path
from uuid import uuid4

# Add backend to path for imports
sys.path.append(str(Path.cwd() / "backend"))

from app.db.database import async_session, init_db
from app.db.models import QuestionDB
from sqlalchemy import select, delete

# --- CONFIGURATION ---
BASE_DATA_DIR = Path("backend/data/images")
# ---------------------

# Default QuestionTypes per subject (Generic fallback)
DEFAULT_TYPES = {
    "maths": "number_operations",
    "non_verbal_reasoning": "nvr_visual",  # Generic NVR
    "verbal_reasoning": "vr_multiple_meaning", # Generic VR
    "english": "grammar"
}

async def update_questions():
    await init_db()
    
    # Find all granular directories
    granular_dirs = glob.glob(str(BASE_DATA_DIR / "granular_*"))
    
    for d in granular_dirs:
        dir_path = Path(d)
        dir_name = dir_path.name
        
        # Extract subject key: granular_maths -> maths
        subject_key = dir_name.replace("granular_", "")
        metadata_file = dir_path / "metadata.json"
        
        if not metadata_file.exists():
            print(f"Skipping {subject_key}: No metadata.json")
            continue
            
        print(f"Processing Subject: {subject_key}")
        
        with open(metadata_file) as f:
            questions_data = json.load(f)
            
        print(f"  Loaded {len(questions_data)} questions")
        
        async with async_session() as session:
            # Delete existing questions for this subject
            stmt = delete(QuestionDB).where(QuestionDB.subject == subject_key)
            result = await session.execute(stmt)
            print(f"  Deleted {result.rowcount} existing questions")
            
            count = 0
            for q_data in questions_data:
                # Construct Content JSON
                content = {
                    "text": q_data.get("text", ""),
                    "options": q_data.get("options", ["A", "B", "C", "D", "E"])
                }

                # Map images to content if present (New Segregated Logic)
                if q_data.get("question_image"):
                     img_filename = q_data["question_image"]
                     content["image_url"] = f"/images/{dir_name}/{img_filename}"
                
                if q_data.get("images"):
                     content["images"] = [f"/images/{dir_name}/{img}" for img in q_data["images"]]
                     
                     # Fallback for legacy extraction (if ques image is missing but images list has it)
                     if "image_url" not in content and content["images"]:
                         # Just a heuristic, might change
                         content["image_url"] = content["images"][0]
                
                # Handling for subjects with NO images (e.g. English comprehension text might be stored differently?)
                # For now assume text is enough.
                
                # Correct Answer & Explanation
                # Ensure answer is A-E
                answer_val = q_data.get("answer", "A")
                if len(str(answer_val)) > 1:
                     # If answer is "FEN", mapping is hard without index. 
                     # But unified script now guarantees "A", "B", "C"... via index logic.
                     pass 
                
                # Auto-detect multi-select based on Answer format (e.g. "A, C")
                if "," in answer_val:
                    content["multi_select"] = True
                
                explanation_val = q_data.get("explanation", "")
                
                # Determine valid QuestionType
                q_type = DEFAULT_TYPES.get(subject_key, "number_operations")

                db_question = QuestionDB(
                    id=str(uuid4()),
                    subject=subject_key,
                    question_type=q_type, 
                    format="multiple_choice",
                    difficulty=3,
                    content=json.dumps(content),
                    answer=json.dumps({"value": answer_val}),
                    explanation=explanation_val,
                    hints=json.dumps([]),
                    tags=json.dumps([]),
                    source="CGP Sample"
                )
                session.add(db_question)
                count += 1
            
            await session.commit()
            print(f"  Added {count} questions for {subject_key}.")

if __name__ == "__main__":
    asyncio.run(update_questions())
