import asyncio
import json
import sys
from pathlib import Path
from sqlalchemy import select

sys.path.append(str(Path(__file__).parent.parent))
from app.db.database import async_session, init_db
from app.db.models import QuestionDB

async def update_images():
    await init_db()
    
    # Filenames from "ls"
    nvr_images = [
        "nvr_q1_new_1769258272956.png",
        "nvr_q2_new_1769258311057.png",
        "nvr_q3_new_1769258334657.png",
        "nvr_q4_new_1769258359467.png",
        "nvr_q5_new_1769258385463.png"
    ]
    maths_bar = "maths_q3_bar_1769258858603.png"

    async with async_session() as session:
        # Update NVR
        stmt = select(QuestionDB).where(QuestionDB.subject == 'non_verbal_reasoning')
        result = await session.execute(stmt)
        nvr_questions = result.scalars().all()
        
        # Sort by content text length or something stable to ensure deterministic mapping?
        # Since I just ingested them, order might be stable.
        nvr_questions.sort(key=lambda x: str(x.id)) # Arbitrary stable sort
        
        for i, q in enumerate(nvr_questions):
            if i < len(nvr_images):
                try:
                    content = json.loads(q.content)
                    content['image_url'] = f"/images/{nvr_images[i]}"
                    content['option_images'] = []
                    # Keep options as lowercase "a", "b"... to match PracticeClient logic
                    content['options'] = ["a", "b", "c", "d", "e"]
                    
                    q.content = json.dumps(content)
                    # Force type to likely match NVR style
                    q.question_type = "nvr_spatial_3d" 
                    session.add(q)
                    print(f"Updated NVR Q {q.id} with {nvr_images[i]}")
                except Exception as e:
                    print(f"Error updating NVR Q {q.id}: {e}")

        # Update Maths
        stmt = select(QuestionDB).where(QuestionDB.subject == 'maths')
        result = await session.execute(stmt)
        maths_questions = result.scalars().all()
        
        for q in maths_questions:
            content = json.loads(q.content)
            text_lower = content['text'].lower()
            if "bar chart" in text_lower or (content.get('options') and "The numbers don't add up" in str(content['options'])):
                content['image_url'] = f"/images/{maths_bar}"
                q.content = json.dumps(content)
                session.add(q)
                print(f"Updated Maths question '{content['text'][:20]}...' with image")
                
        await session.commit()
        print("Database update complete.")

if __name__ == "__main__":
    asyncio.run(update_images())
