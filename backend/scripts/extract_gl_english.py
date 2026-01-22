"""
Extract English questions from GL Assessment PDF test booklets.

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
SAMPLES_DIR = PROJECT_ROOT / "samples" / "English" / "1"
OUTPUT_JSON = PROJECT_ROOT / "backend" / "data" / "questions" / "gl_english_imported.json"
PASSAGES_DIR = PROJECT_ROOT / "backend" / "data" / "passages" / "english"

OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
PASSAGES_DIR.mkdir(parents=True, exist_ok=True)

# English Test Booklet Section Mapping (based on actual PDF structure)
# Format: (start_q, end_q, question_type, section_title, passage_name)
SECTION_MAPPING_BOOKLET_1 = [
    # Comprehension - The Swiss Family Robinson
    (1, 28, "comprehension", "Reading Comprehension", "The Swiss Family Robinson"),

    # Spelling Exercise
    (29, 37, "spelling", "Spelling", None),

    # Punctuation - Hippos
    (38, 46, "grammar", "Punctuation", "Hippos"),

    # Grammar/Cloze - Performance Time
    (47, 54, "grammar", "Grammar", "Performance Time"),
]


def get_section_info(q_num: int, booklet_num: int = 1) -> tuple[str, str, Optional[str]]:
    """Get question type, section title, and passage name for a question number."""
    mapping = SECTION_MAPPING_BOOKLET_1 if booklet_num == 1 else SECTION_MAPPING_BOOKLET_1

    for start, end, q_type, title, passage in mapping:
        if start <= q_num <= end:
            return q_type, title, passage
    return "english", "Unknown", None


def parse_answer_key(extractor: VectorExtractor, page_num: int) -> dict[int, str]:
    """Parse answers from a Parent's Guide page."""
    answers = {}
    text = extractor.extract_text(page_num)

    # Format: "1.\t\nB\n" - answer is on next line after question number
    pattern = r'(\d+)\.\t?\n([A-EN])\n'
    matches = re.findall(pattern, text)

    for q_num_str, answer in matches:
        q_num = int(q_num_str)
        answers[q_num] = answer

    return answers


def extract_all_answers(parents_guide_path: Path) -> dict[int, str]:
    """
    Extract all answers from Parent's Guide.
    Returns dict: {q_num: answer}
    """
    all_answers = {}

    with VectorExtractor(parents_guide_path) as extractor:
        print(f"Parent's Guide has {extractor.page_count} pages")

        # Pages 5 and 6 contain answers for English Familiarisation 1 and 2
        for page_idx in [5, 6]:
            if page_idx < extractor.page_count:
                answers = parse_answer_key(extractor, page_idx)
                all_answers.update(answers)
                print(f"Page {page_idx}: Found {len(answers)} answers")

    return all_answers


def extract_passage(extractor: VectorExtractor, start_page: int, end_page: int) -> str:
    """Extract passage text from consecutive pages."""
    passage = ""

    for page_idx in range(start_page, end_page + 1):
        text = extractor.extract_text(page_idx)
        passage += text + "\n"

    # Clean up the passage
    passage = re.sub(r'Page \d+\s*', '', passage)
    passage = re.sub(r'Please go on to the next page >>>.*', '', passage)
    passage = re.sub(r'\n{3,}', '\n\n', passage)

    return passage.strip()


def extract_questions_from_page(
    extractor: VectorExtractor,
    page_idx: int,
    answers: dict[int, str]
) -> list[dict]:
    """Extract question details from a page."""
    questions = []
    text = extractor.extract_text(page_idx)
    words = extractor.extract_words(page_idx)

    # Find question numbers in the text
    q_pattern = re.compile(r'^\s*(\d{1,2})\s*$', re.MULTILINE)

    # Find question numbers in left margin
    q_positions = []
    for w in words:
        if w['text'].isdigit():
            num = int(w['text'])
            if 1 <= num <= 60 and float(w['x0']) < 70:
                q_positions.append({
                    'num': num,
                    'top': float(w['top']),
                })

    return q_positions


def build_question(
    q_num: int,
    answer: str,
    q_type: str,
    section_title: str,
    passage_name: Optional[str],
    question_text: str,
    options: list[str],
    source_file: str
) -> dict:
    """Build a question object with proper structure."""

    # Build content
    content = {
        "text": question_text,
        "options": options,
    }

    # Add passage reference if applicable
    if passage_name:
        content["passage_ref"] = passage_name

    explanation = f"Section: {section_title}. The correct answer is: {answer}"

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
        "explanation": explanation,
        "tags": ["gl-assessment", section_title.lower().replace(" ", "-")],
        "source": source_file
    }

    return question


def parse_english_booklet(
    booklet_path: Path,
    booklet_num: int,
    answers: dict[int, str]
) -> list[dict]:
    """
    Parse an English test booklet with detailed question extraction.
    """
    questions = []

    with VectorExtractor(booklet_path) as extractor:
        print(f"\nProcessing {booklet_path.name} ({extractor.page_count} pages)")

        # Build mapping of question positions across pages
        q_locations = {}  # {q_num: (page_idx, top_y)}
        page_text_cache = {}  # {page_idx: text}

        for page_idx in range(extractor.page_count):
            words = extractor.extract_words(page_idx)
            page_text = extractor.extract_text(page_idx)
            page_text_cache[page_idx] = page_text

            # Find question numbers in left margin or at specific positions
            for w in words:
                if w['text'].isdigit():
                    num = int(w['text'])
                    if 1 <= num <= 60:
                        # Check if it's in question number position (left side)
                        if float(w['x0']) < 70:
                            if num not in q_locations:
                                q_locations[num] = (page_idx, float(w['top']))

        print(f"Found {len(q_locations)} question locations")

        # Extract each question
        for q_num, answer in sorted(answers.items()):
            q_type, section_title, passage_name = get_section_info(q_num, booklet_num)

            # Default options A-E (or A-E + N for spelling/punctuation)
            if q_type in ["spelling", "grammar"] and section_title in ["Spelling", "Punctuation"]:
                options = ["A", "B", "C", "D", "N"]
            else:
                options = ["A", "B", "C", "D", "E"]

            # Try to extract actual question text
            question_text = f"Q{q_num}."
            if q_num in q_locations:
                page_idx, q_top = q_locations[q_num]
                page_text = page_text_cache.get(page_idx, "")

                # Try to extract a portion of the question text
                # This is simplified - full extraction would parse the PDF more carefully
                question_text = f"Q{q_num}. (See test booklet for full question)"

            q = build_question(
                q_num=q_num,
                answer=answer,
                q_type=q_type,
                section_title=section_title,
                passage_name=passage_name,
                question_text=question_text,
                options=options,
                source_file=booklet_path.name
            )

            questions.append(q)

    return questions


def extract_passage_text(booklet_path: Path) -> dict[str, str]:
    """
    Extract passage texts from the booklet.
    Returns dict of passage_name -> passage_text
    """
    passages = {}

    with VectorExtractor(booklet_path) as extractor:
        # Extract The Swiss Family Robinson passage (pages 1-2)
        passage = ""
        for page_idx in [1, 2]:
            text = extractor.extract_text(page_idx)
            passage += text + "\n"

        # Clean up
        passage = re.sub(r'Page \d+\s*', '', passage)
        passage = re.sub(r'Please go on to the next page >>>.*', '', passage)
        passages["The Swiss Family Robinson"] = passage.strip()

    return passages


def main():
    """Main extraction function."""
    print("GL English Extraction")
    print("=" * 50)

    # Paths
    parents_guide = SAMPLES_DIR / "English_Parent's Guide.pdf"
    booklet_path = SAMPLES_DIR / "English_1_Test Booklet.pdf"

    # Check files exist
    if not parents_guide.exists():
        print(f"Error: Parent's Guide not found at {parents_guide}")
        return

    if not booklet_path.exists():
        print(f"Error: Test booklet not found at {booklet_path}")
        return

    # Extract all answers first
    print("\n1. Extracting answers from Parent's Guide...")
    answers = extract_all_answers(parents_guide)
    print(f"Total answers found: {len(answers)}")

    # Process the booklet
    print("\n2. Processing English Booklet...")
    questions = parse_english_booklet(booklet_path, 1, answers)
    print(f"Extracted {len(questions)} questions")

    # Extract passages
    print("\n3. Extracting passages...")
    passages = extract_passage_text(booklet_path)
    for name, text in passages.items():
        passage_file = PASSAGES_DIR / f"{name.replace(' ', '_').lower()}.txt"
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

    print(f"\nTotal: {len(questions)} English questions extracted")


if __name__ == "__main__":
    main()
