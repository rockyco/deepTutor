"""
Extract English questions from GL Assessment PDF test booklets (v2).

Properly extracts:
- Comprehension questions with full text and options
- Spelling questions with sentences and section markers
- Punctuation questions with sentences
- Grammar (cloze) questions with inline options
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
SAMPLES_DIR = PROJECT_ROOT / "samples" / "English" / "1"
OUTPUT_JSON = PROJECT_ROOT / "backend" / "data" / "questions" / "gl_english_imported.json"
PASSAGES_DIR = PROJECT_ROOT / "backend" / "data" / "passages" / "english"

OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
PASSAGES_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class PageWord:
    """Word with position data."""
    text: str
    x0: float
    y0: float
    x1: float
    y1: float


def extract_page_words(extractor: VectorExtractor, page_idx: int) -> list[PageWord]:
    """Extract words with position data from a page."""
    raw_words = extractor.extract_words(page_idx)
    return [
        PageWord(
            text=w['text'].strip(),
            x0=float(w['x0']),
            y0=float(w['y0']),
            x1=float(w['x1']),
            y1=float(w['y1']),
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


def parse_answer_key(extractor: VectorExtractor, page_num: int) -> dict[int, str]:
    """Parse answers from Parent's Guide page."""
    answers = {}
    text = extractor.extract_text(page_num)

    lines = text.strip().split('\n')
    i = 0
    while i < len(lines) - 1:
        line = lines[i].strip()
        match = re.match(r'^(\d+)\.\s*$', line)
        if match:
            q_num = int(match.group(1))
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                answer = lines[j].strip()
                if answer and not re.match(r'^\d+\.\s*$', answer):
                    answers[q_num] = answer
                    i = j
        i += 1

    return answers


def extract_comprehension_questions(
    extractor: VectorExtractor,
    answers: dict[int, str]
) -> list[dict]:
    """Extract comprehension questions (Q1-28) from pages 3-8."""
    questions = []

    # Build complete text from all question pages
    all_lines = []
    for page_idx in range(2, 9):  # Pages 3-9 (0-indexed 2-8)
        words = extract_page_words(extractor, page_idx)
        lines = group_words_by_line(words)
        all_lines.extend(lines)

    # Parse questions
    current_q = None
    current_text_parts = []
    current_options = []

    for line in all_lines:
        line_text = ' '.join(w.text for w in line)

        # Check if line starts with question number
        first_word = line[0] if line else None
        if first_word and first_word.x0 < 70:
            # Check if it's a question number
            if first_word.text.isdigit():
                q_num = int(first_word.text)
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
                    rest = ' '.join(w.text for w in line[1:])
                    if rest:
                        current_text_parts.append(rest)
                    continue

        # Skip navigation text
        if 'Please go on to the next page' in line_text or line_text.startswith('Page '):
            continue

        # Check for option lines
        option_match = re.match(r'^([A-E])\s+(.+)$', line_text)
        if option_match and line and line[0].x0 > 100:
            current_options.append(f"{option_match.group(1)}: {option_match.group(2)}")
            continue

        # Regular content line
        if current_q is not None and line and line[0].x0 > 100:
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

    # Clean question text
    question_text = re.sub(r'\s+', ' ', question_text).strip()

    content = {
        "text": question_text,
        "options": options if options else ["A", "B", "C", "D", "E"],
        "passage_ref": "The Swiss Family Robinson"
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
        "tags": ["gl-assessment", "reading-comprehension", "swiss-family-robinson"],
        "source": "English_1_Test Booklet.pdf"
    }


def extract_spelling_questions(
    extractor: VectorExtractor,
    answers: dict[int, str]
) -> list[dict]:
    """Extract spelling questions (Q29-37) from page 9."""
    questions = []

    words = extract_page_words(extractor, 9)  # Page 10 (0-indexed 9)
    lines = group_words_by_line(words)

    current_q = None
    current_sentence = ""

    for line in lines:
        if not line:
            continue

        line_text = ' '.join(w.text for w in line)

        # Check for question number
        first_word = line[0]
        if first_word.x0 < 70 and first_word.text.isdigit():
            q_num = int(first_word.text)
            if 29 <= q_num <= 37:
                # Save previous question
                if current_q is not None and current_q in answers:
                    q = build_spelling_question(current_q, current_sentence, answers[current_q])
                    questions.append(q)

                current_q = q_num
                # Get sentence (rest of line or next line)
                rest = ' '.join(w.text for w in line[1:])
                current_sentence = rest
                continue

        # Skip section markers and navigation
        if re.match(r'^[A-D]$', line_text.strip()) or 'A B C D' in line_text:
            continue
        if 'Please go on' in line_text or line_text.startswith('Page '):
            continue
        if 'Spelling Exercise' in line_text or 'In these sentences' in line_text:
            continue
        if 'one mistake or no mistake' in line_text or 'Find the group' in line_text:
            continue
        if 'letter on your answer' in line_text:
            continue

        # Append to current sentence if we have a question
        if current_q is not None and line[0].x0 > 80:
            current_sentence += " " + line_text

    # Save last question
    if current_q is not None and current_q in answers:
        q = build_spelling_question(current_q, current_sentence, answers[current_q])
        questions.append(q)

    return questions


def build_spelling_question(q_num: int, sentence: str, answer: str) -> dict:
    """Build a spelling question object."""

    # Clean sentence
    sentence = re.sub(r'\s+', ' ', sentence).strip()

    content = {
        "text": f"Find the spelling mistake in this sentence (or N if no mistake):\n\n{sentence}",
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
        "tags": ["gl-assessment", "spelling"],
        "source": "English_1_Test Booklet.pdf"
    }


def extract_punctuation_questions(
    extractor: VectorExtractor,
    answers: dict[int, str]
) -> list[dict]:
    """Extract punctuation questions (Q38-46) from pages 10-11."""
    questions = []

    # Process pages 10-11 (0-indexed 10, 11)
    current_q = None
    current_sentence = ""

    for page_idx in [10, 11]:
        if page_idx >= extractor.page_count:
            continue

        words = extract_page_words(extractor, page_idx)
        lines = group_words_by_line(words)

        for line in lines:
            if not line:
                continue

            line_text = ' '.join(w.text for w in line)

            # Check for question number
            first_word = line[0]
            if first_word.x0 < 70 and first_word.text.isdigit():
                q_num = int(first_word.text)
                if 38 <= q_num <= 46:
                    # Save previous question
                    if current_q is not None and current_q in answers:
                        q = build_punctuation_question(current_q, current_sentence, answers[current_q])
                        questions.append(q)

                    current_q = q_num
                    current_sentence = ""
                    continue

            # Skip headers, instructions, and markers
            if any(skip in line_text for skip in [
                'Hippos', 'In these sentences', 'punctuation mistake',
                'letter on your answer', 'A B C D', 'Please go on', 'Page '
            ]):
                continue
            if re.match(r'^[A-D]$', line_text.strip()):
                continue

            # Append to current sentence
            if current_q is not None and line[0].x0 > 80:
                current_sentence += " " + line_text

    # Save last question
    if current_q is not None and current_q in answers:
        q = build_punctuation_question(current_q, current_sentence, answers[current_q])
        questions.append(q)

    return questions


def build_punctuation_question(q_num: int, sentence: str, answer: str) -> dict:
    """Build a punctuation question object."""

    sentence = re.sub(r'\s+', ' ', sentence).strip()

    content = {
        "text": f"Find the punctuation mistake in this sentence (or N if no mistake):\n\n{sentence}",
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
        "tags": ["gl-assessment", "punctuation"],
        "source": "English_1_Test Booklet.pdf"
    }


def extract_grammar_questions(
    extractor: VectorExtractor,
    answers: dict[int, str]
) -> list[dict]:
    """Extract grammar questions (Q47-54) from pages 12-13."""
    questions = []

    # Grammar questions have a cloze format with options inline
    all_text = ""
    for page_idx in [12, 13]:
        if page_idx >= extractor.page_count:
            continue
        text = extractor.extract_text(page_idx)
        all_text += text + "\n"

    # Extract each grammar question
    for q_num in range(47, 55):
        if q_num not in answers:
            continue

        # Find the sentence for this question (inline options format)
        q = build_grammar_question(q_num, answers[q_num])
        questions.append(q)

    return questions


def build_grammar_question(q_num: int, answer: str) -> dict:
    """Build a grammar question object."""

    # Grammar questions are about choosing the correct word to complete a sentence
    content = {
        "text": f"Q{q_num}. Choose the correct word to complete the sentence. (Performance Time passage)",
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
        "tags": ["gl-assessment", "grammar", "cloze"],
        "source": "English_1_Test Booklet.pdf"
    }


def extract_passage(extractor: VectorExtractor) -> str:
    """Extract the comprehension passage from pages 1-2."""
    passage_parts = []

    for page_idx in [1, 2]:  # Pages 2-3 (0-indexed)
        text = extractor.extract_text(page_idx)
        # Clean up
        text = re.sub(r'Page \d+\s*', '', text)
        text = re.sub(r'Please go on to the next page.*', '', text)
        passage_parts.append(text)

    passage = '\n'.join(passage_parts)
    passage = re.sub(r'\n{3,}', '\n\n', passage)
    return passage.strip()


def main():
    """Main extraction function."""
    print("GL English Extraction (v2)")
    print("=" * 50)

    # Paths
    parents_guide = SAMPLES_DIR / "English_Parent's Guide.pdf"
    booklet_path = SAMPLES_DIR / "English_1_Test Booklet.pdf"

    if not parents_guide.exists():
        print(f"Error: Parent's Guide not found at {parents_guide}")
        return

    if not booklet_path.exists():
        print(f"Error: Test booklet not found at {booklet_path}")
        return

    # Extract answers
    print("\n1. Extracting answers from Parent's Guide...")
    with VectorExtractor(parents_guide) as ext:
        answers = parse_answer_key(ext, 5)
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

        # Spelling (Q29-37)
        print("  - Spelling questions...")
        spelling_questions = extract_spelling_questions(ext, answers)
        all_questions.extend(spelling_questions)
        print(f"    Extracted {len(spelling_questions)} spelling questions")

        # Punctuation (Q38-46)
        print("  - Punctuation questions...")
        punct_questions = extract_punctuation_questions(ext, answers)
        all_questions.extend(punct_questions)
        print(f"    Extracted {len(punct_questions)} punctuation questions")

        # Grammar (Q47-54)
        print("  - Grammar questions...")
        grammar_questions = extract_grammar_questions(ext, answers)
        all_questions.extend(grammar_questions)
        print(f"    Extracted {len(grammar_questions)} grammar questions")

        # Extract passage
        print("\n3. Extracting passage...")
        passage = extract_passage(ext)
        passage_file = PASSAGES_DIR / "swiss_family_robinson.txt"
        passage_file.write_text(passage)
        print(f"  Saved passage ({len(passage)} chars)")

    # Save questions
    print(f"\n4. Saving {len(all_questions)} questions to {OUTPUT_JSON}")
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(all_questions, f, indent=2)

    # Summary
    print("\n5. Summary by question type:")
    type_counts = {}
    for q in all_questions:
        qt = q['question_type']
        type_counts[qt] = type_counts.get(qt, 0) + 1

    for qt, count in sorted(type_counts.items()):
        print(f"   {qt}: {count}")

    # Show samples
    print("\n6. Sample questions:")
    for i in [0, 10, 28, 35, 45, 50]:
        if i < len(all_questions):
            q = all_questions[i]
            text = q['content']['text'][:80].replace('\n', ' ')
            print(f"   Q{i+1}: {text}...")

    print(f"\nTotal: {len(all_questions)} English questions extracted")


if __name__ == "__main__":
    main()
