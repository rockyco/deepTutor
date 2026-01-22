"""
Extract English questions from CGP 11+ Sample Paper PDF (v2).

Extracts:
- Comprehension questions about two passages (Mi Nuong, Secret Garden)
- Spelling questions (passage format with sections A-D)
- Punctuation questions
- Grammar (cloze) questions
"""

import re
import json
import uuid
import sys
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

# Direct import from vector_extractor module
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR / "app" / "crawlers"))

from vector_extractor import VectorExtractor

# Configuration
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SAMPLES_DIR = PROJECT_ROOT / "samples" / "English" / "2"
OUTPUT_JSON = PROJECT_ROOT / "backend" / "data" / "questions" / "cgp_english_imported.json"

OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class PageWord:
    """Word with position data."""
    text: str
    x0: float
    y0: float


def extract_page_words(extractor: VectorExtractor, page_idx: int) -> list[PageWord]:
    """Extract words with position data from a page."""
    raw_words = extractor.extract_words(page_idx)
    return [
        PageWord(
            text=w['text'].strip(),
            x0=float(w['x0']),
            y0=float(w['y0']),
        )
        for w in raw_words
        if w['text'].strip()
    ]


def group_words_by_line(words: list[PageWord], tolerance: float = 8.0) -> list[list[PageWord]]:
    """Group words into lines based on vertical position."""
    if not words:
        return []

    sorted_words = sorted(words, key=lambda w: (w.y0, w.x0))
    lines = []
    current_line = [sorted_words[0]]
    current_y = sorted_words[0].y0

    for word in sorted_words[1:]:
        if abs(word.y0 - current_y) <= tolerance:
            current_line.append(word)
        else:
            lines.append(sorted(current_line, key=lambda w: w.x0))
            current_line = [word]
            current_y = word.y0

    if current_line:
        lines.append(sorted(current_line, key=lambda w: w.x0))

    return lines


def parse_mark_scheme(extractor: VectorExtractor) -> dict[int, str]:
    """Parse answers from CGP mark scheme."""
    answers = {}
    text = extractor.extract_text(0)

    # Format: "1)\t B —" or "1) B —"
    pattern = r'(\d+)\)\s*([A-EN])\s*[—-]'
    matches = re.findall(pattern, text)

    for q_num_str, answer in matches:
        q_num = int(q_num_str)
        answers[q_num] = answer

    return answers


def extract_comprehension_questions(
    extractor: VectorExtractor,
    answers: dict[int, str]
) -> list[dict]:
    """Extract comprehension questions (Q1-28) from the booklet."""
    questions = []

    # Collect all lines from question pages
    all_lines = []
    for page_idx in range(6):  # Pages 0-5 have comprehension
        words = extract_page_words(extractor, page_idx)
        lines = group_words_by_line(words)
        all_lines.extend(lines)

    # Parse questions
    current_q = None
    current_text_parts = []
    current_options = []

    for line in all_lines:
        line_text = ' '.join(w.text for w in line)

        # Skip headers, footers, navigation
        if any(skip in line_text for skip in [
            'Sample Test', 'CGP 2018', 'cgpbooks.co.uk', 'Carry on',
            'answer sheet', 'Read this passage', 'Answer these questions',
            'Circle the letter', '/ 2'
        ]):
            continue

        # Check for question number pattern: "3." or "3.\t"
        q_match = re.match(r'^(\d+)\.\s*(.*)$', line_text)
        if q_match:
            q_num = int(q_match.group(1))
            if 1 <= q_num <= 28:
                # Save previous question
                if current_q is not None and current_q in answers:
                    q = build_comprehension_question(
                        current_q,
                        ' '.join(current_text_parts),
                        current_options,
                        answers[current_q]
                    )
                    questions.append(q)

                # Start new question
                current_q = q_num
                current_text_parts = []
                current_options = []

                # Get rest of line as question text
                rest = q_match.group(2)
                if rest:
                    current_text_parts.append(rest)
                continue

        # Check for option lines (A, B, C, D, E at start)
        option_match = re.match(r'^([A-E])\s+(.+)$', line_text)
        if option_match:
            current_options.append(f"{option_match.group(1)}: {option_match.group(2)}")
            continue

        # Regular content line - append to question
        if current_q is not None and line_text.strip():
            current_text_parts.append(line_text)

    # Save last question
    if current_q is not None and current_q in answers:
        q = build_comprehension_question(
            current_q,
            ' '.join(current_text_parts),
            current_options,
            answers[current_q]
        )
        questions.append(q)

    return questions


def build_comprehension_question(
    q_num: int,
    question_text: str,
    options: list[str],
    answer: str
) -> dict:
    """Build a comprehension question object."""

    # Determine passage reference
    if q_num <= 14:
        passage_ref = "The Crystal Heart (Mi Nuong)"
        tags = ["cgp-assessment", "reading-comprehension", "crystal-heart"]
    else:
        passage_ref = "The Secret Garden"
        tags = ["cgp-assessment", "reading-comprehension", "secret-garden"]

    # Clean question text
    question_text = re.sub(r'\s+', ' ', question_text).strip()

    content = {
        "text": question_text,
        "options": options if options else ["A", "B", "C", "D", "E"],
        "passage_ref": passage_ref
    }

    return {
        "id": str(uuid.uuid4()),
        "subject": "english",
        "question_type": "comprehension",
        "format": "multiple_choice",
        "difficulty": 3,
        "content": content,
        "answer": {"value": answer, "case_sensitive": False},
        "explanation": f"Reading Comprehension: The correct answer is {answer}",
        "tags": tags,
        "source": "CGP-11-Plus-English-Sample-Paper.pdf"
    }


def extract_spelling_questions(
    extractor: VectorExtractor,
    answers: dict[int, str]
) -> list[dict]:
    """Extract spelling questions (Q29-34) from page 6."""
    questions = []

    # Page 6 (index 6) has spelling
    text = extractor.extract_text(6)

    # Extract sentences for each question
    # Format: "29. sentence with A B C D N markers"
    for q_num in range(29, 35):
        if q_num not in answers:
            continue

        q = build_spelling_question(q_num, answers[q_num])
        questions.append(q)

    return questions


def build_spelling_question(q_num: int, answer: str) -> dict:
    """Build a spelling question object."""

    content = {
        "text": f"Q{q_num}. Find the spelling mistake in this line (or N if no mistake). (Adventure Trail passage)",
        "options": ["A", "B", "C", "D", "N"],
    }

    return {
        "id": str(uuid.uuid4()),
        "subject": "english",
        "question_type": "spelling",
        "format": "multiple_choice",
        "difficulty": 3,
        "content": content,
        "answer": {"value": answer, "case_sensitive": False},
        "explanation": f"Spelling: The correct answer is {answer}",
        "tags": ["cgp-assessment", "spelling"],
        "source": "CGP-11-Plus-English-Sample-Paper.pdf"
    }


def extract_punctuation_questions(
    extractor: VectorExtractor,
    answers: dict[int, str]
) -> list[dict]:
    """Extract punctuation questions (Q35-40) from page 7."""
    questions = []

    for q_num in range(35, 41):
        if q_num not in answers:
            continue

        q = build_punctuation_question(q_num, answers[q_num])
        questions.append(q)

    return questions


def build_punctuation_question(q_num: int, answer: str) -> dict:
    """Build a punctuation question object."""

    content = {
        "text": f"Q{q_num}. Find the punctuation mistake in this line (or N if no mistake).",
        "options": ["A", "B", "C", "D", "N"],
    }

    return {
        "id": str(uuid.uuid4()),
        "subject": "english",
        "question_type": "punctuation",
        "format": "multiple_choice",
        "difficulty": 3,
        "content": content,
        "answer": {"value": answer, "case_sensitive": False},
        "explanation": f"Punctuation: The correct answer is {answer}",
        "tags": ["cgp-assessment", "punctuation"],
        "source": "CGP-11-Plus-English-Sample-Paper.pdf"
    }


def extract_grammar_questions(
    extractor: VectorExtractor,
    answers: dict[int, str]
) -> list[dict]:
    """Extract grammar questions (Q41-50) from page 7."""
    questions = []

    for q_num in range(41, 51):
        if q_num not in answers:
            continue

        q = build_grammar_question(q_num, answers[q_num])
        questions.append(q)

    return questions


def build_grammar_question(q_num: int, answer: str) -> dict:
    """Build a grammar question object."""

    content = {
        "text": f"Q{q_num}. Choose the correct word to complete the sentence. (Dear Diary passage)",
        "options": ["A", "B", "C", "D", "E"],
    }

    return {
        "id": str(uuid.uuid4()),
        "subject": "english",
        "question_type": "grammar",
        "format": "multiple_choice",
        "difficulty": 3,
        "content": content,
        "answer": {"value": answer, "case_sensitive": False},
        "explanation": f"Grammar: The correct answer is {answer}",
        "tags": ["cgp-assessment", "grammar", "cloze"],
        "source": "CGP-11-Plus-English-Sample-Paper.pdf"
    }


def main():
    """Main extraction function."""
    print("CGP English Extraction (v2)")
    print("=" * 50)

    # Paths
    booklet_path = SAMPLES_DIR / "CGP-11-Plus-English-Sample-Paper Homework.pdf"
    mark_scheme_path = SAMPLES_DIR / "CGP-11-Plus-English-Sample-Paper-Mark-Scheme Homework.pdf"

    if not booklet_path.exists():
        print(f"Error: Booklet not found at {booklet_path}")
        return

    if not mark_scheme_path.exists():
        print(f"Error: Mark scheme not found at {mark_scheme_path}")
        return

    # Extract answers from mark scheme
    print("\n1. Extracting answers from mark scheme...")
    with VectorExtractor(mark_scheme_path) as ext:
        answers = parse_mark_scheme(ext)
        print(f"  Found {len(answers)} answers")

    # Extract questions
    print("\n2. Extracting questions from test booklet...")
    all_questions = []

    with VectorExtractor(booklet_path) as ext:
        # Comprehension (Q1-28)
        print("  - Comprehension questions...")
        comp_questions = extract_comprehension_questions(ext, answers)
        all_questions.extend(comp_questions)
        print(f"    Extracted {len(comp_questions)} comprehension questions")

        # Spelling (Q29-34)
        print("  - Spelling questions...")
        spelling_questions = extract_spelling_questions(ext, answers)
        all_questions.extend(spelling_questions)
        print(f"    Extracted {len(spelling_questions)} spelling questions")

        # Punctuation (Q35-40)
        print("  - Punctuation questions...")
        punct_questions = extract_punctuation_questions(ext, answers)
        all_questions.extend(punct_questions)
        print(f"    Extracted {len(punct_questions)} punctuation questions")

        # Grammar (Q41-50)
        print("  - Grammar questions...")
        grammar_questions = extract_grammar_questions(ext, answers)
        all_questions.extend(grammar_questions)
        print(f"    Extracted {len(grammar_questions)} grammar questions")

    # Save questions
    print(f"\n3. Saving {len(all_questions)} questions to {OUTPUT_JSON}")
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(all_questions, f, indent=2)

    # Summary
    print("\n4. Summary by question type:")
    type_counts = {}
    for q in all_questions:
        qt = q['question_type']
        type_counts[qt] = type_counts.get(qt, 0) + 1

    for qt, count in sorted(type_counts.items()):
        print(f"   {qt}: {count}")

    # Show samples
    print("\n5. Sample questions:")
    for i in [0, 10, 20, 28, 35, 45]:
        if i < len(all_questions):
            q = all_questions[i]
            text = q['content']['text'][:80].replace('\n', ' ')
            print(f"   Q{i+1}: {text}...")

    print(f"\nTotal: {len(all_questions)} CGP English questions extracted")


if __name__ == "__main__":
    main()
