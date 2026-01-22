"""
Extract English questions from CGP 11+ Sample Paper.

Extracts comprehension, spelling, punctuation, and grammar questions.
"""

import re
import json
import uuid
import sys
from pathlib import Path
from typing import Optional

# Direct import from vector_extractor module
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR / "app" / "crawlers"))

from vector_extractor import VectorExtractor

# Configuration
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SAMPLES_DIR = PROJECT_ROOT / "samples" / "English" / "2"
OUTPUT_JSON = PROJECT_ROOT / "backend" / "data" / "questions" / "cgp_english_imported.json"
PASSAGES_DIR = PROJECT_ROOT / "backend" / "data" / "passages" / "english"

OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
PASSAGES_DIR.mkdir(parents=True, exist_ok=True)

# CGP Paper Section Mapping
# Format: (start_q, end_q, question_type, section_title, passage_name)
SECTION_MAPPING = [
    # Comprehension - The Crystal Heart
    (1, 14, "comprehension", "Reading Comprehension", "The Crystal Heart"),

    # Comprehension - The Secret Garden
    (15, 28, "comprehension", "Reading Comprehension", "The Secret Garden"),

    # Spelling mistakes
    (29, 34, "spelling", "Spelling", None),

    # Punctuation mistakes
    (35, 40, "grammar", "Punctuation", None),

    # Grammar/Cloze - Dear Diary
    (41, 50, "grammar", "Grammar", "Dear Diary"),
]


def get_section_info(q_num: int) -> tuple[str, str, Optional[str]]:
    """Get question type, section title, and passage name for a question number."""
    for start, end, q_type, title, passage in SECTION_MAPPING:
        if start <= q_num <= end:
            return q_type, title, passage
    return "english", "Unknown", None


def parse_mark_scheme(extractor: VectorExtractor) -> dict[int, dict]:
    """
    Parse the CGP mark scheme.
    Returns dict: {q_num: {'answer': str, 'explanation': str}}
    """
    answers = {}

    text = extractor.extract_text(0)

    # Parse answers in format: "1)\tB - explanation"
    # Or "1) B - explanation"
    pattern = r'(\d+)\)[\t\s]+([A-EN])\s*[—-]?\s*(.+?)(?=\d+\)|\Z)'
    matches = re.findall(pattern, text, re.DOTALL)

    for q_num_str, answer, explanation in matches:
        q_num = int(q_num_str)
        # Clean up explanation
        explanation = explanation.strip()
        explanation = re.sub(r'\s+', ' ', explanation)

        answers[q_num] = {
            'answer': answer.strip(),
            'explanation': explanation[:200] if len(explanation) > 200 else explanation
        }

    return answers


def build_question(
    q_num: int,
    answer_data: dict,
    q_type: str,
    section_title: str,
    passage_name: Optional[str],
    source_file: str
) -> dict:
    """Build a question object with proper structure."""

    answer = answer_data['answer']
    explanation = answer_data.get('explanation', f"The correct answer is: {answer}")

    # Build content
    content = {
        "text": f"Q{q_num}. (See test booklet for full question)",
    }

    # Determine options based on section
    if q_type == "spelling" or (q_type == "grammar" and section_title == "Punctuation"):
        content["options"] = ["A", "B", "C", "D", "N"]
    elif q_type == "grammar" and section_title == "Grammar":
        content["options"] = ["A", "B", "C", "D", "E"]
    else:
        content["options"] = ["A", "B", "C", "D", "E"]

    # Add passage reference if applicable
    if passage_name:
        content["passage_ref"] = passage_name

    question = {
        "id": str(uuid.uuid4()),
        "subject": "english",
        "question_type": q_type,
        "format": "multiple_choice",
        "difficulty": 3,
        "content": content,
        "answer": {
            "value": answer,
            "case_sensitive": False
        },
        "explanation": f"Section: {section_title}. {explanation}",
        "tags": ["cgp", "gl-assessment", section_title.lower().replace(" ", "-")],
        "source": source_file
    }

    return question


def extract_passage_text(booklet_path: Path) -> dict[str, str]:
    """
    Extract passage texts from the booklet.
    Returns dict of passage_name -> passage_text
    """
    passages = {}

    with VectorExtractor(booklet_path) as extractor:
        # Extract The Crystal Heart passage (page 0)
        text = extractor.extract_text(0)
        # Find the passage portion
        passage_match = re.search(r'The Crystal Heart\s*Read.*?\n(.+?)(?=\d+\.\s+)', text, re.DOTALL)
        if passage_match:
            passages["The Crystal Heart"] = passage_match.group(1).strip()

        # Extract The Secret Garden passage (page 3)
        text = extractor.extract_text(3)
        passage_match = re.search(r"An extract from 'The Secret Garden'.*?\n(.+?)(?=\d+\.\s+)", text, re.DOTALL)
        if passage_match:
            passages["The Secret Garden"] = passage_match.group(1).strip()

    return passages


def main():
    """Main extraction function."""
    print("CGP English Extraction")
    print("=" * 50)

    # Paths
    mark_scheme = SAMPLES_DIR / "CGP-11-Plus-English-Sample-Paper-Mark-Scheme Homework.pdf"
    booklet_path = SAMPLES_DIR / "CGP-11-Plus-English-Sample-Paper Homework.pdf"

    # Check files exist
    if not mark_scheme.exists():
        print(f"Error: Mark scheme not found at {mark_scheme}")
        return

    if not booklet_path.exists():
        print(f"Error: Test booklet not found at {booklet_path}")
        return

    # Extract all answers from mark scheme
    print("\n1. Extracting answers from Mark Scheme...")
    with VectorExtractor(mark_scheme) as extractor:
        answers = parse_mark_scheme(extractor)
    print(f"Total answers found: {len(answers)}")

    # Build questions
    print("\n2. Building questions...")
    questions = []

    for q_num, answer_data in sorted(answers.items()):
        q_type, section_title, passage_name = get_section_info(q_num)

        q = build_question(
            q_num=q_num,
            answer_data=answer_data,
            q_type=q_type,
            section_title=section_title,
            passage_name=passage_name,
            source_file=booklet_path.name
        )

        questions.append(q)

    print(f"Built {len(questions)} questions")

    # Extract passages
    print("\n3. Extracting passages...")
    passages = extract_passage_text(booklet_path)
    for name, text in passages.items():
        passage_file = PASSAGES_DIR / f"{name.replace(' ', '_').lower()}_cgp.txt"
        passage_file.write_text(text)
        print(f"   Saved passage: {name} ({len(text)} chars)")

    # Save to JSON
    print(f"\n4. Saving {len(questions)} questions to {OUTPUT_JSON}")
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(questions, f, indent=2)

    # Print summary by type
    print("\n5. Summary by question type:")
    type_counts = {}
    for q in questions:
        qt = q['question_type']
        type_counts[qt] = type_counts.get(qt, 0) + 1

    for qt, count in sorted(type_counts.items()):
        print(f"   {qt}: {count}")

    print(f"\nTotal: {len(questions)} CGP English questions extracted")


if __name__ == "__main__":
    main()
