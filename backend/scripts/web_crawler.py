#!/usr/bin/env python3
"""
Web Crawler for GL Assessment Content
Fetches questions from various online sources and ingests into DeepTutor DB.
"""

import asyncio
import json
import logging
import html
import re
import sys
import httpx
from pathlib import Path
from typing import List, Dict, Any

# Ensure backend directory is in python path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.database import async_session, init_db
from app.db.models import QuestionDB
from sqlalchemy import text as sa_text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================
# DATA SOURCES
# =============================================

OPENTDB_MATHS_URL = "https://opentdb.com/api.php?amount=50&category=19&type=multiple"
OPENTDB_SCIENCE_URL = "https://opentdb.com/api.php?amount=50&category=17&type=multiple"

# =============================================
# HELPER FUNCTIONS
# =============================================

def clean_html(text: str) -> str:
    """Decode HTML entities and clean text."""
    return html.unescape(text)

def parse_opentdb_question(item: Dict[str, Any], subject: str) -> Dict[str, Any]:
    """Parse an OpenTDB question into our schema."""
    options = item["incorrect_answers"] + [item["correct_answer"]]
    # Shuffle options but track correct index
    import random
    random.shuffle(options)
    correct_idx = options.index(item["correct_answer"])
    
    return {
        "subject": subject,
        "question_type": "number_operations" if subject == "maths" else "comprehension",
        "difficulty": {"easy": 1, "medium": 3, "hard": 5}.get(item["difficulty"], 3),
        "content": {
            "text": clean_html(item["question"]),
            "options": [clean_html(o) for o in options],
            "images": [],
            "passage": None
        },
        "answer": {
            "value": clean_html(item["correct_answer"]),
            "correct_index": correct_idx
        },
        "source": "OpenTDB"
    }

# =============================================
# VERBAL REASONING QUESTION TEMPLATES
# =============================================

VR_WORD_PAIRS = [
    {"q": "Which word is most similar in meaning to HAPPY?", "opts": ["Joyful", "Sad", "Angry", "Tired"], "ans": "Joyful"},
    {"q": "Which word is the opposite of LARGE?", "opts": ["Huge", "Small", "Giant", "Enormous"], "ans": "Small"},
    {"q": "Choose the word that best completes: The cat ___ on the mat.", "opts": ["sat", "table", "blue", "quickly"], "ans": "sat"},
    {"q": "Which word does NOT belong with the others?", "opts": ["Apple", "Banana", "Carrot", "Orange"], "ans": "Carrot"},
    {"q": "Find the missing letters: C_T (hint: a furry animal)", "opts": ["A", "O", "U", "E"], "ans": "A"},
    {"q": "What is 15 + 27?", "opts": ["42", "32", "52", "41"], "ans": "42"},
    {"q": "Which is the largest: 1/2, 1/4, 3/4, 1/3?", "opts": ["1/2", "1/4", "3/4", "1/3"], "ans": "3/4"},
    {"q": "If today is Monday, what day is it in 3 days?", "opts": ["Thursday", "Wednesday", "Friday", "Tuesday"], "ans": "Thursday"},
    {"q": "Complete the pattern: 2, 4, 6, 8, ?", "opts": ["9", "10", "12", "11"], "ans": "10"},
    {"q": "If A=1, B=2, C=3, what is D+E?", "opts": ["7", "8", "9", "10"], "ans": "9"},
]

# Additional VR questions - synonyms, antonyms, word logic
VR_SYNONYMS = [
    {"q": "Find two words, one from each group, that are closest in meaning.\n(happy, sad, angry) (joyful, tired, hungry)", "opts": ["happy, joyful", "sad, tired", "angry, hungry", "happy, tired"], "ans": "happy, joyful"},
    {"q": "Find two words, one from each group, that are OPPOSITE in meaning.\n(hot, warm, cool) (cold, tepid, mild)", "opts": ["hot, cold", "warm, tepid", "cool, mild", "hot, mild"], "ans": "hot, cold"},
    {"q": "Which word means the same as DIFFICULT?", "opts": ["Hard", "Easy", "Simple", "Light"], "ans": "Hard"},
    {"q": "Which word means the opposite of ANCIENT?", "opts": ["Old", "Modern", "Antique", "Historic"], "ans": "Modern"},
    {"q": "Choose the word closest in meaning to RAPID.", "opts": ["Slow", "Quick", "Steady", "Careful"], "ans": "Quick"},
]

VR_CODES = [
    {"q": "If CAT = DOU, then DOG = ?", "opts": ["EPH", "EPG", "FOH", "FOG"], "ans": "EPH"},
    {"q": "If ABC = 123, then DEF = ?", "opts": ["456", "345", "567", "234"], "ans": "456"},
    {"q": "In a code, TREE is written as USFF. What is PLANT?", "opts": ["QMBOU", "QMASU", "OMBOU", "QMBOT"], "ans": "QMBOU"},
]

VR_SEQUENCES = [
    {"q": "What comes next: A, C, E, G, ?", "opts": ["H", "I", "J", "K"], "ans": "I"},
    {"q": "What comes next: 3, 6, 12, 24, ?", "opts": ["36", "48", "30", "42"], "ans": "48"},
    {"q": "What comes next: Z, X, V, T, ?", "opts": ["S", "R", "Q", "P"], "ans": "R"},
]

def generate_vr_questions() -> List[Dict]:
    """Generate Verbal Reasoning questions from templates."""
    questions = []
    all_templates = VR_WORD_PAIRS + VR_SYNONYMS + VR_CODES + VR_SEQUENCES
    
    for template in all_templates:
        options = template["opts"]
        correct_idx = options.index(template["ans"])
        
        questions.append({
            "subject": "verbal_reasoning",
            "question_type": "vr_synonyms",
            "difficulty": 3,
            "content": {
                "text": template["q"],
                "options": options,
                "images": [],
                "passage": None
            },
            "answer": {
                "value": template["ans"],
                "correct_index": correct_idx
            },
            "source": "Generated VR"
        })
    
    return questions

# =============================================
# NON-VERBAL REASONING (TEXT-BASED LOGIC)
# =============================================

NVR_LOGIC = [
    {"q": "Look at this sequence: ◯ ◼ ◯ ◼ ◯ ? What comes next?", "opts": ["◯", "◼", "△", "◇"], "ans": "◼"},
    {"q": "If all circles are shaded, and a shape has 4 sides, it must be:", "opts": ["A shaded circle", "A square", "A triangle", "Unknown"], "ans": "A square"},
    {"q": "A shape is reflected in a vertical mirror line. If the original points LEFT, the reflection points:", "opts": ["Left", "Right", "Up", "Down"], "ans": "Right"},
    {"q": "A shape is rotated 90 degrees clockwise. An arrow pointing UP will now point:", "opts": ["Left", "Right", "Up", "Down"], "ans": "Right"},
    {"q": "In a pattern, black shapes alternate with white shapes. If the pattern starts black, the 4th shape is:", "opts": ["Black", "White", "Grey", "Striped"], "ans": "White"},
]

def generate_nvr_questions() -> List[Dict]:
    """Generate Non-Verbal Reasoning questions from templates."""
    questions = []
    
    for template in NVR_LOGIC:
        options = template["opts"]
        correct_idx = options.index(template["ans"])
        
        questions.append({
            "subject": "non_verbal_reasoning",
            "question_type": "nvr_sequences",
            "difficulty": 3,
            "content": {
                "text": template["q"],
                "options": options,
                "images": [],
                "passage": None
            },
            "answer": {
                "value": template["ans"],
                "correct_index": correct_idx
            },
            "source": "Generated NVR"
        })
    
    return questions

# =============================================
# ENGLISH COMPREHENSION QUESTIONS
# =============================================

ENGLISH_PASSAGES = [
    {
        "passage": """The old lighthouse stood on the rocky cliff, its white walls weathered by decades of salt spray and storm winds. Every evening, as the sun dipped below the horizon, its powerful beam would sweep across the dark waters, guiding ships safely past the dangerous rocks below.

For generations, the lighthouse keeper's family had lived in the small cottage beside it. They understood the sea's moods—when it lay calm and glittering like broken glass, and when it rose in fury, sending waves crashing against the cliffs with a sound like thunder.""",
        "questions": [
            {"q": "Where is the lighthouse located?", "opts": ["On a beach", "On a rocky cliff", "In a harbour", "On an island"], "ans": "On a rocky cliff"},
            {"q": "What colour are the lighthouse walls?", "opts": ["Grey", "Blue", "White", "Red"], "ans": "White"},
            {"q": "What is the purpose of the lighthouse beam?", "opts": ["To attract fish", "To guide ships safely", "To signal the time", "To warn of storms"], "ans": "To guide ships safely"},
            {"q": "Who lived in the cottage beside the lighthouse?", "opts": ["Sailors", "The lighthouse keeper's family", "Fishermen", "No one"], "ans": "The lighthouse keeper's family"},
            {"q": "What simile is used to describe calm seas?", "opts": ["Like thunder", "Like broken glass", "Like a mirror", "Like silver"], "ans": "Like broken glass"},
        ]
    },
    {
        "passage": """Sarah carefully unwrapped the old journal she had found in her grandmother's attic. The leather cover was cracked with age, and the pages had turned a soft yellow colour. On the first page, written in elegant handwriting, were the words: "The Adventures of Mary Elizabeth Harper, 1923."

As Sarah turned the pages, she discovered her great-grandmother's childhood adventures—climbing the ancient oak tree in the garden, exploring the mysterious caves by the sea, and befriending a stray dog that followed her everywhere. Each entry brought the past to life in vivid detail.""",
        "questions": [
            {"q": "Where did Sarah find the journal?", "opts": ["In the basement", "In her grandmother's attic", "At a shop", "In a library"], "ans": "In her grandmother's attic"},
            {"q": "What year was written on the first page?", "opts": ["1913", "1923", "1933", "1943"], "ans": "1923"},
            {"q": "What had happened to the pages over time?", "opts": ["They had turned yellow", "They had been torn", "They had been folded", "They were blank"], "ans": "They had turned yellow"},
            {"q": "What was one of Mary's childhood adventures?", "opts": ["Swimming in the ocean", "Climbing an oak tree", "Riding horses", "Sailing boats"], "ans": "Climbing an oak tree"},
            {"q": "What kind of animal befriended Mary?", "opts": ["A cat", "A bird", "A stray dog", "A rabbit"], "ans": "A stray dog"},
        ]
    }
]

def generate_english_questions() -> List[Dict]:
    """Generate English Comprehension questions from templates."""
    questions = []
    
    for passage_data in ENGLISH_PASSAGES:
        passage = passage_data["passage"]
        for q_template in passage_data["questions"]:
            options = q_template["opts"]
            correct_idx = options.index(q_template["ans"])
            
            questions.append({
                "subject": "english",
                "question_type": "comprehension",
                "difficulty": 3,
                "content": {
                    "text": q_template["q"],
                    "options": options,
                    "images": [],
                    "passage": passage
                },
                "answer": {
                    "value": q_template["ans"],
                    "correct_index": correct_idx
                },
                "source": "Generated English"
            })
    
    return questions

# =============================================
# MAIN CRAWLER
# =============================================

async def fetch_opentdb_questions() -> List[Dict]:
    """Fetch questions from OpenTDB API."""
    questions = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for url, subject in [(OPENTDB_MATHS_URL, "maths"), (OPENTDB_SCIENCE_URL, "maths")]:
            try:
                response = await client.get(url)
                data = response.json()
                
                if data.get("response_code") == 0:
                    for item in data.get("results", []):
                        q = parse_opentdb_question(item, subject)
                        questions.append(q)
                    logger.info(f"Fetched {len(data.get('results', []))} questions from {url}")
            except Exception as e:
                logger.error(f"Error fetching from {url}: {e}")
    
    return questions

async def clear_database():
    """Clear existing questions."""
    logger.info("Clearing existing questions...")
    async with async_session() as session:
        await session.execute(sa_text("DELETE FROM questions"))
        await session.commit()

async def ingest_questions(questions: List[Dict]):
    """Ingest questions into the database."""
    async with async_session() as session:
        for q in questions:
            db_q = QuestionDB(
                subject=q["subject"],
                question_type=q["question_type"],
                difficulty=q["difficulty"],
                content=json.dumps(q["content"]),
                answer=json.dumps(q["answer"]),
                explanation="",
                source=q["source"]
            )
            session.add(db_q)
        await session.commit()

async def main():
    """Main crawler function."""
    await init_db()
    await clear_database()
    
    all_questions = []
    
    # 1. Fetch from OpenTDB API
    logger.info("Fetching from OpenTDB API...")
    opentdb_questions = await fetch_opentdb_questions()
    all_questions.extend(opentdb_questions)
    logger.info(f"Total from OpenTDB: {len(opentdb_questions)}")
    
    # 2. Generate VR Questions
    logger.info("Generating Verbal Reasoning questions...")
    vr_questions = generate_vr_questions()
    all_questions.extend(vr_questions)
    logger.info(f"Generated VR: {len(vr_questions)}")
    
    # 3. Generate NVR Questions
    logger.info("Generating Non-Verbal Reasoning questions...")
    nvr_questions = generate_nvr_questions()
    all_questions.extend(nvr_questions)
    logger.info(f"Generated NVR: {len(nvr_questions)}")
    
    # 4. Generate English Comprehension Questions
    logger.info("Generating English Comprehension questions...")
    english_questions = generate_english_questions()
    all_questions.extend(english_questions)
    logger.info(f"Generated English: {len(english_questions)}")
    
    # 5. Ingest all questions
    logger.info("Ingesting all questions into database...")
    await ingest_questions(all_questions)
    
    logger.info(f"TOTAL QUESTIONS INGESTED: {len(all_questions)}")

if __name__ == "__main__":
    asyncio.run(main())
