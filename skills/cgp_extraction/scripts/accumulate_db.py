
import asyncio
import json
import sys
import glob
from pathlib import Path
from pathlib import Path
from uuid import uuid5, NAMESPACE_DNS
import hashlib

# Add backend to path for imports
sys.path.append(str(Path.cwd() / "backend"))

from app.db.database import async_session, init_db
from app.db.models import QuestionDB
from sqlalchemy import select

# --- CONFIGURATION ---
BASE_DATA_DIR = Path("backend/data/images")
# ---------------------

# Default QuestionTypes per subject (Generic fallback)
DEFAULT_TYPES = {
    "maths": "number_operations",
    "non_verbal_reasoning": "nvr_visual",
    "verbal_reasoning": "vr_multiple_meaning",
    "english": "grammar"
}

async def accumulate_questions():
    """Reads metadata.json and UPSERTS questions into DB (Accumulate Mode)"""
    await init_db()
    
    # Find all granular directories
    granular_dirs = glob.glob(str(BASE_DATA_DIR / "granular_*"))
    
    total_added = 0
    total_updated = 0
    
    for d in granular_dirs:
        dir_path = Path(d)
        dir_name = dir_path.name
        
        subject_key = dir_name.replace("granular_", "")
        metadata_file = dir_path / "metadata.json"
        
        if not metadata_file.exists():
            continue
            
        print(f"Processing Subject: {subject_key}")
        
        with open(metadata_file) as f:
            questions_data = json.load(f)
            
        async with async_session() as session:
            count = 0
            for q_data in questions_data:
                # 1. Prepare Content
                content = {
                    "text": q_data.get("text", ""),
                    "options": q_data.get("options", ["A", "B", "C", "D", "E"])
                }

                if q_data.get("question_image"):
                     img_filename = q_data["question_image"]
                     content["image_url"] = f"/images/{dir_name}/{img_filename}"
                
                if q_data.get("images"):
                     content["images"] = [f"/images/{dir_name}/{img}" for img in q_data["images"]]
                     if "image_url" not in content and content["images"]:
                         content["image_url"] = content["images"][0]
                     
                     # Reconstruct option_images map
                     q_num = q_data.get("question_num")
                     if q_num and content.get("options"):
                         opt_imgs = [None] * len(content["options"])
                         has_opt_img = False
                         for img_path in content["images"]:
                             # Expected format: .../q{num}_option_{idx}.png
                             # We check the filename at end of path
                             fname = img_path.split("/")[-1]
                             if f"q{q_num}_option_" in fname:
                                 try:
                                     # Extract index between "option_" and ".png"
                                     # Simplest: split by "_" then take last part? No.
                                     # regex is safer but let's do simple string parsing
                                     # q1_option_0.png
                                     idx_part = fname.split("_option_")[1].split(".")[0]
                                     idx = int(idx_part)
                                     if 0 <= idx < len(opt_imgs):
                                         opt_imgs[idx] = img_path
                                         has_opt_img = True
                                 except:
                                     pass
                         
                         if has_opt_img:
                             content["option_images"] = opt_imgs
                
                # 2. Prepare Answer
                answer_val = q_data.get("answer", "A")
                if "," in answer_val:
                    content["multi_select"] = True
                
                explanation_val = q_data.get("explanation", "")
                q_type = DEFAULT_TYPES.get(subject_key, "number_operations")

                # 3. Deterministic ID Generation (Content Hashing)
                # Using Question Text + Subject + Image Hash (for NVR uniqueness)
                unique_string = f"{subject_key}:{content['text'].strip()}"
                
                # Add image hash to distinguish NVR questions with identical text
                img_filename = q_data.get("question_image")
                if not img_filename and q_data.get("images"):
                     img_filename = q_data["images"][0]
                     
                if img_filename:
                    img_path = dir_path / img_filename
                    if img_path.exists():
                        try:
                            with open(img_path, "rb") as f:
                                img_hash = hashlib.md5(f.read()).hexdigest()
                                unique_string += f":{img_hash}"
                        except Exception as e:
                            print(f"Warning: Could not hash image {img_filename}: {e}")

                q_id = str(uuid5(NAMESPACE_DNS, unique_string))

                # 4. Create DB Object
                db_question = QuestionDB(
                    id=q_id,
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
                
                # 5. MERGE (Upsert)
                await session.merge(db_question)
                count += 1
            
            await session.commit()
            print(f"  Processed {count} questions for {subject_key} (Accumulated/Updated).")
            total_added += count

    print(f"\nDONE. Processed {total_added} questions total.")

if __name__ == "__main__":
    asyncio.run(accumulate_questions())
