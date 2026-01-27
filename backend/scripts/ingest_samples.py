
import asyncio
import json
import logging
import base64
from pathlib import Path
import sys
from uuid import uuid4

# Ensure backend directory is in python path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.database import async_session, init_db
from app.db.models import QuestionDB
from app.models.question import QuestionType, Subject
from sqlalchemy import delete

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def infer_question_type(subject: str, text: str, given_type: str = None) -> str:
    """Infer the specific QuestionType."""
    if given_type:
        # Try to map scraped type to enum
        try:
            # Normalize scraped type (e.g. "visual_coding" -> "vr_number_codes" or similar?)
            # For now, simplistic mapping or fallback to text inference
            pass 
        except:
            pass
            
    text = text.lower()
    
    if subject == "maths":
        if any(w in text for w in ["chart", "graph", "table", "data"]):
            return QuestionType.DATA_HANDLING.value
        if any(w in text for w in ["volume", "area", "shape", "angle", "cuboid"]):
            return QuestionType.GEOMETRY.value
        if any(w in text for w in ["fraction", "percent", "ratio"]):
            return QuestionType.FRACTIONS.value
        if any(w in text for w in ["sequence", "term"]):
            return QuestionType.ALGEBRA.value
        return QuestionType.WORD_PROBLEMS.value
        
    elif subject == "english":
        if "spelling" in text:
            return QuestionType.SPELLING.value
        if any(w in text for w in ["punctuation", "capital", "grammar", "verb", "noun", "adjective"]):
            return QuestionType.GRAMMAR.value
        if any(w in text for w in ["meaning", "synonym", "antonym", "metaphor", "simile"]):
            return QuestionType.VOCABULARY.value
        return QuestionType.COMPREHENSION.value
    
    elif subject == "verbal_reasoning":
        if "analogy" in given_type or "is to" in text:
             return QuestionType.VR_WORD_PAIRS.value
        if "code" in text or "code" in str(given_type):
             return QuestionType.VR_NUMBER_CODES.value 
        return QuestionType.VR_LOGIC_PROBLEMS.value # Default
        
    elif subject == "non_verbal_reasoning":
        # Map common NVR types
        if "folding" in text: return QuestionType.NVR_SPATIAL_3D.value
        if "hidden" in text: return QuestionType.NVR_ODD_ONE_OUT.value
        return QuestionType.NVR_SEQUENCES.value # Default

    return "multiple_choice"

def save_base64_image(base64_str: str, subject: str, prefix: str) -> str:
    """Decodes base64 string and saves to disk. Returns the URL path."""
    if not base64_str or not base64_str.startswith('data:image'):
        return None
        
    try:
        header, encoded = base64_str.split(",", 1)
        data = base64.b64decode(encoded)
        
        # Directory setup
        base_dir = Path(__file__).parent.parent.parent # deepTutor
        img_dir = base_dir / "backend" / "data" / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{subject}_{prefix}_{uuid4().hex[:8]}.png"
        file_path = img_dir / filename
        
        with open(file_path, "wb") as f:
            f.write(data)
            
        return f"/images/{filename}"
    except Exception as e:
        logger.error(f"Failed to save image: {e}")
        return None

async def ingest_questions():
    """Ingest questions from multiple scraped JSON files."""
    await init_db()
    
    base_dir = Path(__file__).parent.parent.parent # /home/amd/UTS/deepTutor
    files = [
        base_dir / "data" / "cgp_scraped_maths_english.json",
        base_dir / "data" / "cgp_scraped_vr_nvr.json"
    ]
    
    all_questions = []
    for f_path in files:
        if f_path.exists():
            try:
                with open(f_path, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_questions.extend(data)
            except Exception as e:
                logger.error(f"Error reading {f_path}: {e}")

    async with async_session() as session:
        # Clear existing
        logger.info("Clearing existing questions...")
        await session.execute(delete(QuestionDB))
        
        count = 0
        for q in all_questions:
            subject = q.get('subject', 'maths')
            
            # 1. Handle Main Image
            image_url = None
            if q.get('question_image_src'):
                image_url = save_base64_image(q['question_image_src'], subject, "q")
            
            # 2. Handle Option Images
            option_images = None
            if q.get('options_images'):
                option_images = []
                for idx, img_src in enumerate(q['options_images']):
                    url = save_base64_image(img_src, subject, f"opt_{idx}")
                    option_images.append(url if url else "")

            # 3. Infer Type
            valid_type = infer_question_type(subject, q.get('text', ''), q.get('question_type'))
            
            # 4. Content
            content = {
                "text": q.get('text', ''),
                "options": q.get('options', []),
                "image_url": image_url,
                "option_images": option_images
            }
            
            correct = q['options'][0] if q.get('options') else "A"
            
            db_q = QuestionDB(
                subject=subject,
                question_type=valid_type,
                difficulty=3,
                content=json.dumps(content),
                answer=json.dumps({"value": correct}),
                explanation="Source: CGP Free Sample",
                source="CGP"
            )
            session.add(db_q)
            count += 1
        
        await session.commit()
        logger.info(f"Successfully ingested {count} questions.")

if __name__ == "__main__":
    asyncio.run(ingest_questions())
