
import asyncio
import json
import logging
import re
import sys
import fitz  # PyMuPDF
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

# Ensure backend directory is in python path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.database import async_session, init_db
from app.db.models import QuestionDB
from sqlalchemy import text as sa_text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FRONTEND_PUBLIC_DIR = Path(__file__).parent.parent.parent / "frontend" / "public" / "questions"

@dataclass
class QuestionRegion:
    start_y: float
    end_y: float
    text: str
    number: str
    page_num: int

async def clear_database():
    """Clear existing questions."""
    logger.info("Clearing existing questions...")
    async with async_session() as session:
        await session.execute(sa_text("DELETE FROM questions"))
        await session.commit()

def save_crop(doc, page_num, rect, pdf_name, q_idx) -> str | None:
    """Render a crop of the page to an image and save it."""
    try:
        page = doc[page_num]
        # High resolution render
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect)
        
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', pdf_name)
        output_dir = FRONTEND_PUBLIC_DIR / safe_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"p{page_num}_q{q_idx}.png"
        filepath = output_dir / filename
        
        pix.save(str(filepath))
        return f"/questions/{safe_name}/{filename}"
    except Exception as e:
        logger.error(f"Failed to save crop: {e}")
        return None

def extract_content_from_pdf(pdf_path: Path):
    doc = fitz.open(pdf_path)
    all_questions = []
    
    # Subject Detection
    name = pdf_path.name
    subject = "maths"
    q_type = "number_operations"
    is_nvr = False
    is_english = False
    
    if "English" in name: 
        subject = "english"
        q_type = "comprehension"
        is_english = True
    elif "Non-Verbal" in name: 
        subject = "non_verbal_reasoning"
        q_type = "nvr_sequences"
        is_nvr = True
    elif "Verbal" in name and "Non" not in name:
        subject = "verbal_reasoning"
        q_type = "vr_logic_problems"

    current_passage = ""

    for page_num, page in enumerate(doc):
        # Layout Analysis
        blocks = page.get_text("blocks")
        # Sort by Y then X
        blocks.sort(key=lambda b: (b[1], b[0]))
        
        # Identify Question Markers
        # "1", "1)", "Q1", "P1"
        q_markers = []
        for b in blocks:
            text = b[4].strip()
            # Strict regex for detached numbers or P-numbers
            if re.match(r'^(?:Q|P)?\d+[\.\)\s]*$', text) or re.match(r'^(?:Q|P)?\d+[\.\)\s]+', text):
                q_markers.append(b)

        if not q_markers:
            # If English page and lots of text, maybe it's a passage page?
            if is_english:
                page_text = "\n".join([b[4] for b in blocks])
                if len(page_text) > 500:
                    current_passage += "\n" + page_text
            continue

        # Process Questions on this page
        # Define regions: Marker N -> Marker N+1
        # For last marker, go to bottom of page (minus footer)
        
        page_height = page.rect.height
        
        for i, marker in enumerate(q_markers):
            y_start = marker[1] - 10 # slightly above
            
            # Find next y
            if i < len(q_markers) - 1:
                y_end = q_markers[i+1][1] - 10
            else:
                y_end = page_height - 50 # Footer margin
            
            # Crop Rect
            rect = fitz.Rect(0, y_start, page.rect.width, y_end)
            
            content_text = marker[4] # The text of the marker block usually contains the start of Q
            # Aggregate text in this region?
            # For NVR, we rely on the IMAGE.
            # For English, we rely on TEXT.
            
            # Extract Text in Region
            region_text = ""
            for b in blocks:
                # If block center is within Y range
                mid_y = (b[1] + b[3]) / 2
                if y_start <= mid_y <= y_end:
                    region_text += b[4] + "\n"
            
            # Clean text (remove the marker itself roughly)
            clean_text = re.sub(r'^(?:Q|P)?\d+[\.\)\s]*', '', region_text).strip()
            
            q_data = {
                "subject": subject,
                "question_type": q_type,
                "difficulty": 3,
                "content": {
                    "text": clean_text,
                    "options": [], 
                    "images": [],
                    "passage": current_passage if is_english else None
                },
                "answer": {"value": "Unknown", "correct_index": 0},
                "source": name
            }

            # NVR Strategy: Always generate an image of the region
            # This captures the shapes perfectly.
            # Even for maths/english, it's a good fallback "visual".
            # Let's save it for NVR specifically.
            if is_nvr:
                img_url = save_crop(doc, page_num, rect, pdf_path.stem, len(all_questions))
                if img_url:
                    q_data['content']['images'].append(img_url)
                    # Clear text if it's just artifacts, but keeping it is fine.
            
            all_questions.append(q_data)

    return all_questions

async def ingest_v4():
    await init_db()
    await clear_database()
    
    base_dir = Path(__file__).parent.parent.parent # /home/amd/UTS/deepTutor
    samples_dir = base_dir / "samples"
    
    async with async_session() as session:
        total = 0
        for pdf_file in samples_dir.rglob("*.pdf"):
            # SKIP ANSWERS
            if "Answer" in pdf_file.name or "Mark" in pdf_file.name:
                continue
                
            logger.info(f"Processing V4 {pdf_file.name}...")
            questions = extract_content_from_pdf(pdf_file)
            
            for q in questions:
                db_q = QuestionDB(
                    subject=q['subject'],
                    question_type=q['question_type'],
                    difficulty=q['difficulty'],
                    content=json.dumps(q['content']),
                    answer=json.dumps(q['answer']),
                    explanation="",
                    source=q['source']
                )
                session.add(db_q)
            
            await session.commit()
            total += len(questions)
            logger.info(f"Ingested {len(questions)} from {pdf_file.name}")
            
    logger.info(f"Total questions ingested: {total}")

if __name__ == "__main__":
    asyncio.run(ingest_v4())
