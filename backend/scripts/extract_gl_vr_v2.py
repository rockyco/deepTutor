"""
Extract Verbal Reasoning questions from GL Assessment PDF test booklets (v2).

Improved extraction that properly:
- Filters out instruction blocks and examples
- Separates question content from option letters
- Handles different VR question types correctly
"""

import re
import json
import uuid
import sys
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

# Direct import from vector_extractor module
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR / "app" / "crawlers"))

from vector_extractor import VectorExtractor

# Configuration
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SAMPLES_DIR = PROJECT_ROOT / "samples" / "VR" / "2"
OUTPUT_JSON = PROJECT_ROOT / "backend" / "data" / "questions" / "gl_vr_imported.json"

OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class QuestionSection:
    """Defines a section of VR questions with its type and parsing rules."""
    start_q: int
    end_q: int
    question_type: str
    title: str
    instruction: str
    format: str = "fill_in_blank"  # fill_in_blank or multiple_choice
    has_options: bool = False  # Whether question has A B C D E options


# Section definitions for VR Familiarisation booklets
# Based on actual PDF structure analysis
SECTIONS_BOOKLET_1 = [
    QuestionSection(1, 7, "vr_insert_letter", "Move a Letter",
        "One letter can be moved from the first word to the second word to make two new words. Find the letter that moves."),
    QuestionSection(8, 14, "vr_insert_letter", "Complete Words",
        "The same letter must fit into both sets of brackets to complete the word in front and begin the word after."),
    QuestionSection(15, 21, "vr_word_pairs", "Word Patterns",
        "The three words in the second group should go together in the same way as the first group. Find the missing word.",
        has_options=True),
    QuestionSection(22, 28, "vr_number_series", "Number Series",
        "Find the number that continues the series in the most sensible way."),
    QuestionSection(29, 29, "vr_logic_problems", "Logic Problem",
        "Read the information and find the correct answer.", has_options=True),
    QuestionSection(30, 37, "vr_synonyms", "Opposites",
        "Find two words, one from each group, that are most opposite in meaning.",
        format="multiple_choice", has_options=True),
    QuestionSection(38, 44, "vr_hidden_word", "Hidden Words",
        "Find the pair of words that contain a hidden four-letter word.",
        format="multiple_choice", has_options=True),
    QuestionSection(45, 51, "vr_letter_series", "Letter Series",
        "Find the next pair of letters in the series.", has_options=True),
    QuestionSection(52, 59, "vr_missing_word", "Missing Letters",
        "Three letters have been removed from the word. Find the three-letter word.",
        has_options=True),
    QuestionSection(60, 66, "vr_word_pairs", "Word Relationships",
        "Find the two words that complete the sentence best.",
        format="multiple_choice", has_options=True),
    QuestionSection(67, 67, "vr_logic_problems", "Logic",
        "Only one sentence must be true. Which one?",
        format="multiple_choice", has_options=True),
    QuestionSection(68, 74, "vr_multiple_meaning", "Multiple Meanings",
        "Find the word that goes equally well with both pairs.",
        has_options=True),
    QuestionSection(75, 80, "vr_number_codes", "Codes",
        "Work out which number represents which letter. Find the code or word."),
]

# Booklets 2 and 3 have similar structure but may have slight variations
SECTIONS_BOOKLET_2 = SECTIONS_BOOKLET_1.copy()
SECTIONS_BOOKLET_3 = SECTIONS_BOOKLET_1.copy()


def get_section_for_question(q_num: int, booklet_num: int = 1) -> Optional[QuestionSection]:
    """Get the section definition for a question number."""
    sections = {1: SECTIONS_BOOKLET_1, 2: SECTIONS_BOOKLET_2, 3: SECTIONS_BOOKLET_3}
    for section in sections.get(booklet_num, SECTIONS_BOOKLET_1):
        if section.start_q <= q_num <= section.end_q:
            return section
    return None


def parse_answer_key(extractor: VectorExtractor, page_num: int) -> dict[int, str]:
    """
    Parse answers from Parent's Guide page.

    Format in PDF:
    29.\t
    3
    30.\t
    hit, miss
    """
    answers = {}
    text = extractor.extract_text(page_num)

    # Split into lines and parse pairs
    lines = text.strip().split('\n')
    i = 0
    while i < len(lines) - 1:
        line = lines[i].strip()
        # Match question number line: "29.\t" or "29."
        match = re.match(r'^(\d+)\.\s*$', line)
        if match:
            q_num = int(match.group(1))
            # Next non-empty line is the answer
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


def extract_all_answers(parents_guide_path: Path) -> dict[int, dict[int, str]]:
    """
    Extract all answers from Parent's Guide.
    Returns: {booklet_num: {q_num: answer}}
    """
    all_answers = {}

    with VectorExtractor(parents_guide_path) as extractor:
        print(f"Parent's Guide: {extractor.page_count} pages")

        # Pages 5, 6, 7 contain answers for booklets 1, 2, 3 (0-indexed)
        for booklet_num in [1, 2, 3]:
            page_idx = 4 + booklet_num  # Pages 5, 6, 7
            if page_idx < extractor.page_count:
                answers = parse_answer_key(extractor, page_idx)
                all_answers[booklet_num] = answers
                print(f"  Booklet {booklet_num}: {len(answers)} answers")

    return all_answers


@dataclass
class PageWord:
    """Word with position data."""
    text: str
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def top(self) -> float:
        return self.y0


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


def is_question_number(word: PageWord, margin_x: float = 60.0) -> Optional[int]:
    """Check if word is a question number in the left margin."""
    if word.x0 > margin_x:
        return None
    if word.text.isdigit():
        num = int(word.text)
        if 1 <= num <= 80:
            return num
    return None


def is_instruction_or_example(line_text: str) -> bool:
    """Check if line is part of instruction or example block."""
    patterns = [
        r'^In (this|these) question',
        r'^The letters must',
        r'^Find the letter',
        r'^Mark (both|it|your)',
        r'^Example\s',
        r'^Answer\s',
        r'^Solution\s',
        r'^The answer is',
        r'on the answer sheet',
        r'on your answer sheet',
        r'^The alphabet is here',
        r'^Work out which',
        r'^If these statements',
        r'^Read the information',
        r'^Only one of the',
        r'^The three words',
        r'^The same letter',
        r'^One letter can be moved',
        r'^Three letters.*taken out',
        r'^A word of (four|three) letters',
        r'Please go on to the next page',
        r'^Page \d+$',
    ]

    for pattern in patterns:
        if re.search(pattern, line_text, re.IGNORECASE):
            return True
    return False


def is_option_label_line(line_text: str) -> bool:
    """Check if line contains only option labels like 'A m B e C t D a E l'."""
    # Pattern for spaced option letters with content
    if re.match(r'^[A-E]\s+\S+\s+[A-E]\s+\S+', line_text):
        return True
    # Pattern for option answer lines like "A break   X poke"
    if re.match(r'^[A-E]\s+\S+\s+[XYZ]\s+\S+', line_text):
        return True
    return False


def strip_option_labels(line_text: str) -> str:
    """
    Remove option label patterns from content.

    Patterns to remove:
    - "A m B e C t D a E l" (letter labels with single chars)
    - "A answer B answer C answer D answer E answer" (multiple choice options)
    """
    # Pattern for "A x B y C z D w E v" at end of line (VR insert letter type)
    # This matches option labels with single characters
    line_text = re.sub(r'\s+A\s+\S\s+B\s+\S\s+C\s+\S\s+D\s+\S\s+E\s+\S\s*$', '', line_text)

    # Also strip any trailing option line that starts with A
    # e.g., "A tan B tee C ten D tar E tab"
    line_text = re.sub(r'\s+A\s+\S+\s+B\s+\S+\s+C\s+\S+\s+D\s+\S+\s+E\s+\S+\s*$', '', line_text)

    return line_text.strip()


def extract_question_content(
    lines: list[list[PageWord]],
    q_num: int,
    q_line_idx: int,
    next_q_line_idx: Optional[int],
    section: QuestionSection
) -> tuple[str, list[str]]:
    """
    Extract question content and options from lines between question numbers.

    Returns: (question_text, options_list)
    """
    content_parts = []
    options = []

    # Process lines from question number to next question (or end)
    end_idx = next_q_line_idx if next_q_line_idx else len(lines)

    for i in range(q_line_idx, min(end_idx, len(lines))):
        line_words = lines[i]
        if not line_words:
            continue

        # Skip words in left margin (including question number itself)
        content_words = [w for w in line_words if w.x0 > 70]
        if not content_words:
            continue

        line_text = ' '.join(w.text for w in content_words)

        # Skip instruction/example lines
        if is_instruction_or_example(line_text):
            continue

        # Handle option lines based on question type
        if section.has_options:
            # Check for labeled options (A answer B answer...)
            opt_match = re.match(r'^([A-E])\s+(.+?)(?:\s+([A-E])\s+(.+?))*$', line_text)
            if opt_match and re.match(r'^[A-E]\s+\S+\s+[A-E]', line_text):
                # Parse individual options
                opt_pattern = r'([A-E])\s+(\S+)'
                for m in re.finditer(opt_pattern, line_text):
                    options.append(f"{m.group(1)}: {m.group(2)}")
                continue

            # Check for single option lines like "A answer"
            single_opt = re.match(r'^([A-E])\s+(.+)$', line_text)
            if single_opt and len(line_text) < 50:
                options.append(f"{single_opt.group(1)}: {single_opt.group(2)}")
                continue

        # Regular content line - strip any trailing option labels
        cleaned_line = strip_option_labels(line_text)
        if cleaned_line:
            content_parts.append(cleaned_line)

    question_text = ' '.join(content_parts).strip()

    # Clean up question text
    question_text = re.sub(r'\s+', ' ', question_text)
    question_text = re.sub(r'\[\s*\?\s*\]', '[?]', question_text)

    # Additional cleanup for any remaining option patterns
    question_text = strip_option_labels(question_text)

    return question_text, options


def extract_questions_from_booklet(
    booklet_path: Path,
    booklet_num: int,
    answers: dict[int, str]
) -> list[dict]:
    """Extract all questions from a VR test booklet."""
    questions = []

    with VectorExtractor(booklet_path) as extractor:
        print(f"Processing {booklet_path.name} ({extractor.page_count} pages)")

        # Build a map of question number -> (page_idx, line_idx, lines)
        q_locations = {}  # {q_num: (page_idx, line_idx)}
        all_page_lines = {}  # {page_idx: lines}

        for page_idx in range(extractor.page_count):
            words = extract_page_words(extractor, page_idx)
            lines = group_words_by_line(words)
            all_page_lines[page_idx] = lines

            for line_idx, line_words in enumerate(lines):
                for word in line_words:
                    q_num = is_question_number(word)
                    if q_num and q_num not in q_locations:
                        q_locations[q_num] = (page_idx, line_idx)

        print(f"  Found {len(q_locations)} question positions")

        # Extract each question
        for q_num, answer in sorted(answers.items()):
            section = get_section_for_question(q_num, booklet_num)
            if not section:
                print(f"  Warning: No section for Q{q_num}")
                continue

            # Get location
            if q_num not in q_locations:
                print(f"  Warning: Q{q_num} not found in PDF")
                continue

            page_idx, line_idx = q_locations[q_num]
            lines = all_page_lines[page_idx]

            # Find next question line on same page
            next_line_idx = None
            for next_q in range(q_num + 1, q_num + 10):
                if next_q in q_locations:
                    next_page, next_l = q_locations[next_q]
                    if next_page == page_idx:
                        next_line_idx = next_l
                        break

            # Extract content
            q_text, options = extract_question_content(
                lines, q_num, line_idx, next_line_idx, section
            )

            # Build question object
            question = build_question(
                q_num=q_num,
                answer=answer,
                question_text=q_text,
                options=options,
                section=section,
                booklet_num=booklet_num,
                source_file=booklet_path.name
            )

            questions.append(question)

    return questions


def build_question(
    q_num: int,
    answer: str,
    question_text: str,
    options: list[str],
    section: QuestionSection,
    booklet_num: int,
    source_file: str
) -> dict:
    """Build a question object with proper structure."""

    # Determine format and prepare options
    if section.format == "multiple_choice" or options:
        q_format = "multiple_choice"
        if not options:
            options = ["A", "B", "C", "D", "E"]
    else:
        q_format = "fill_in_blank"
        options = None

    # Build content text
    if question_text:
        content_text = f"{section.instruction}\n\n{question_text}"
    else:
        content_text = section.instruction

    # Build content dict
    content = {"text": content_text}
    if options:
        content["options"] = options

    # Process answer for case sensitivity
    answer_value = answer
    if q_format == "fill_in_blank":
        answer_value = answer.lower()

    question = {
        "id": str(uuid.uuid4()),
        "subject": "verbal_reasoning",
        "question_type": section.question_type,
        "format": q_format,
        "difficulty": 3,
        "content": content,
        "answer": {
            "value": answer_value,
            "case_sensitive": False
        },
        "explanation": f"{section.title}: The correct answer is {answer}",
        "tags": [
            "gl-assessment",
            section.title.lower().replace(" ", "-"),
            f"booklet-{booklet_num}"
        ],
        "source": source_file
    }

    return question


def main():
    """Main extraction function."""
    print("GL Verbal Reasoning Extraction (v2)")
    print("=" * 50)

    # Paths
    parents_guide = SAMPLES_DIR / "Verbal Reasoning_Parent's Guide.pdf"
    booklet_files = [
        ("Verbal Reasoning_1_Test Booklet.pdf", 1),
        ("Verbal Reasoning_2_Test Booklet.pdf", 2),
        ("Verbal Reasoning_3_Test Booklet.pdf", 3),
    ]

    # Check files exist
    if not parents_guide.exists():
        print(f"Error: Parent's Guide not found at {parents_guide}")
        return

    # Extract all answers
    print("\n1. Extracting answers from Parent's Guide...")
    all_answers = extract_all_answers(parents_guide)

    # Process each booklet
    all_questions = []

    for filename, booklet_num in booklet_files:
        booklet_path = SAMPLES_DIR / filename

        if not booklet_path.exists():
            print(f"Warning: {filename} not found, skipping")
            continue

        if booklet_num not in all_answers:
            print(f"Warning: No answers for booklet {booklet_num}, skipping")
            continue

        print(f"\n2.{booklet_num}. Processing Booklet {booklet_num}...")
        answers = all_answers[booklet_num]

        questions = extract_questions_from_booklet(booklet_path, booklet_num, answers)
        all_questions.extend(questions)

        print(f"   Extracted {len(questions)} questions")

    # Save to JSON
    print(f"\n3. Saving {len(all_questions)} questions to {OUTPUT_JSON}")
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(all_questions, f, indent=2)

    # Print summary
    print("\n4. Summary by question type:")
    type_counts = {}
    for q in all_questions:
        qt = q['question_type']
        type_counts[qt] = type_counts.get(qt, 0) + 1

    for qt, count in sorted(type_counts.items()):
        print(f"   {qt}: {count}")

    # Show samples
    print("\n5. Sample questions:")
    for i in [0, 10, 30, 50, 70]:
        if i < len(all_questions):
            q = all_questions[i]
            text = q['content']['text'][:100].replace('\n', ' ')
            print(f"   Q{i+1}: {text}...")

    print(f"\nTotal: {len(all_questions)} VR questions extracted")


if __name__ == "__main__":
    main()
