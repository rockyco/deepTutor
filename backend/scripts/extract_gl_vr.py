"""
Extract Verbal Reasoning questions from GL Assessment PDF test booklets.

Extracts text-based VR questions and maps answers from the Parent's Guide.
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
SAMPLES_DIR = PROJECT_ROOT / "samples" / "VR" / "2"
OUTPUT_JSON = PROJECT_ROOT / "backend" / "data" / "questions" / "gl_vr_imported.json"

OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

# VR Test Booklet Section Mapping (based on actual PDF structure)
# Format: (start_q, end_q, question_type, section_title, instruction_text)
SECTION_MAPPING = [
    # Insert letter - move letter from first word to second word
    (1, 7, "vr_insert_letter", "Move a Letter",
     "One letter can be moved from the first word to the second word to make two new words. Find the letter that moves."),

    # Fill bracket letter - same letter completes both words
    (8, 14, "vr_insert_letter", "Complete Words",
     "The same letter must fit into both sets of brackets to complete the word in front and begin the word after."),

    # Word patterns - find the missing word based on pattern
    (15, 21, "vr_word_pairs", "Word Patterns",
     "The three words in the second group should go together in the same way as the first group. Find the missing word."),

    # Number series - find the next number
    (22, 28, "vr_number_series", "Number Series",
     "Find the number that continues the series in the most sensible way."),

    # Logic problem - word problem requiring reasoning
    (29, 29, "vr_logic_problems", "Logic Problem",
     "Read the information and find the correct answer to the question."),

    # Antonyms - find opposite word pairs
    (30, 37, "vr_synonyms", "Opposites",
     "Find two words, one from each group, that are most opposite in meaning."),

    # Hidden word - find 4-letter word hidden between words
    (38, 44, "vr_hidden_word", "Hidden Words",
     "A word of four letters is hidden at the end of one word and the beginning of the next. Find the pair of words containing the hidden word."),

    # Letter series - find next letter pair
    (45, 51, "vr_letter_series", "Letter Series",
     "Find the next pair of letters in the series."),

    # Missing letters - three letters removed from word
    (52, 59, "vr_missing_word", "Missing Letters",
     "The word in capitals has had three letters next to each other taken out. These three letters make one correctly-spelt word."),

    # Word analogies - complete the relationship
    (60, 66, "vr_word_pairs", "Word Relationships",
     "Find the two words, one from each group, that will complete the sentence in the best way."),

    # Logic - multiple choice reasoning
    (67, 67, "vr_logic_problems", "Logic",
     "If these statements are true, only one of the sentences below must be true. Which one?"),

    # Multiple meanings - word fits both pairs
    (68, 74, "vr_multiple_meaning", "Multiple Meanings",
     "Only one of the five possible answers will go equally well with both pairs of words."),

    # Codes - letter-number codes
    (75, 80, "vr_number_codes", "Codes",
     "Work out which number represents which letter. Find the code or word."),
]


def get_section_info(q_num: int) -> tuple[str, str, str]:
    """Get question type, section title, and instruction text for a question number."""
    for start, end, q_type, title, text in SECTION_MAPPING:
        if start <= q_num <= end:
            return q_type, title, text
    return "verbal_reasoning", "Unknown", "Select the correct answer."


def parse_answer_key(extractor: VectorExtractor, page_num: int) -> dict[int, str]:
    """Parse answers from a Parent's Guide page."""
    answers = {}
    text = extractor.extract_text(page_num)

    # Format is: "29.\t\n3\n" - answer is on next line after question number
    # Use regex to match: number + dot + tab + newline + answer
    pattern = r'(\d+)\.\t\n(.+?)(?=\n\d+\.\t|\n*$)'
    matches = re.findall(pattern, text, re.DOTALL)

    for q_num_str, answer in matches:
        q_num = int(q_num_str)
        # Clean up the answer - may span multiple lines for some answers
        answer = answer.strip()
        # Replace newlines within answer with spaces (for multi-line answers)
        answer = re.sub(r'\n+', ' ', answer).strip()
        if answer:
            answers[q_num] = answer

    return answers


def extract_all_answers(parents_guide_path: Path) -> dict[int, dict[int, str]]:
    """
    Extract all answers from Parent's Guide.
    Returns dict: {booklet_num: {q_num: answer}}
    """
    all_answers = {}

    with VectorExtractor(parents_guide_path) as extractor:
        print(f"Parent's Guide has {extractor.page_count} pages")

        # Pages 5, 6, 7 contain answers for booklets 1, 2, 3 (0-indexed)
        for booklet_num in [1, 2, 3]:
            page_idx = 4 + booklet_num  # Pages 5, 6, 7 (0-indexed)
            if page_idx < extractor.page_count:
                answers = parse_answer_key(extractor, page_idx)
                all_answers[booklet_num] = answers
                print(f"Booklet {booklet_num}: Found {len(answers)} answers")

    return all_answers


def extract_question_text_by_page(extractor: VectorExtractor, page_idx: int) -> list[dict]:
    """
    Extract questions from a page of the test booklet.
    Returns list of dicts with question number, raw text, and options.
    """
    text = extractor.extract_text(page_idx)
    words = extractor.extract_words(page_idx)

    questions = []

    # Find question numbers in the text
    # Questions are numbered 1-80, typically in left margin
    q_pattern = re.compile(r'^(\d{1,2})\s*$', re.MULTILINE)

    # Find all positions of question numbers
    q_positions = []
    for w in words:
        if w['text'].isdigit() and 1 <= int(w['text']) <= 80:
            # Check if it's in the left margin (x0 < 70)
            if float(w['x0']) < 70:
                q_positions.append({
                    'num': int(w['text']),
                    'top': float(w['top']),
                    'text': w['text']
                })

    # Sort by vertical position
    q_positions.sort(key=lambda x: x['top'])

    return q_positions


def extract_question_content(text: str, q_num: int, next_q_start: Optional[int] = None) -> dict:
    """
    Extract question content from text between question numbers.
    """
    # This is simplified - in practice we'd need more sophisticated parsing
    # based on the specific question type
    return {
        'q_num': q_num,
        'raw_text': text.strip()
    }


def build_question(
    q_num: int,
    answer: str,
    booklet_num: int,
    source_file: str
) -> dict:
    """
    Build a question object with proper structure.
    """
    q_type, section_title, instruction = get_section_info(q_num)

    # Determine format based on question type
    # VR questions can be fill_in_blank or multiple_choice
    # Multiple choice types need options A-E
    multiple_choice_types = [
        "vr_synonyms",  # Antonyms/Synonyms - select word pairs
        "vr_word_pairs",  # Word patterns
        "vr_hidden_word",  # Hidden word in sentences
        "vr_logic_problems",  # Logic problems with options
    ]

    if q_type in multiple_choice_types:
        q_format = "multiple_choice"
        options = ["A", "B", "C", "D", "E"]
    else:
        q_format = "fill_in_blank"
        options = None  # No options for fill-in-blank

    # Build explanation
    explanation = f"Section: {section_title}. The correct answer is: {answer}"

    # Build content
    content = {
        "text": f"Question {q_num}: {instruction}",
    }

    # Only add options if present
    if options:
        content["options"] = options

    question = {
        "id": str(uuid.uuid4()),
        "subject": "verbal_reasoning",
        "question_type": q_type,
        "format": q_format,
        "difficulty": 3,
        "content": content,
        "answer": {
            "value": answer.lower() if isinstance(answer, str) else answer,
            "case_sensitive": False
        },
        "explanation": explanation,
        "tags": ["gl-assessment", section_title.lower().replace(" ", "-"), f"booklet-{booklet_num}"],
        "source": source_file
    }

    return question


def extract_detailed_questions(booklet_path: Path, booklet_num: int, answers: dict[int, str]) -> list[dict]:
    """
    Extract detailed question content from a test booklet.
    """
    questions = []

    with VectorExtractor(booklet_path) as extractor:
        print(f"\nProcessing {booklet_path.name} ({extractor.page_count} pages)")

        # Process each page to extract full question text
        full_text = ""
        for page_idx in range(extractor.page_count):
            page_text = extractor.extract_text(page_idx)
            full_text += f"\n--- PAGE {page_idx} ---\n{page_text}"

        # For each question number in answers, create a question
        for q_num, answer in sorted(answers.items()):
            q = build_question(q_num, answer, booklet_num, booklet_path.name)

            # Try to extract the actual question text from the PDF
            q_text = extract_question_text_from_full(full_text, q_num)
            if q_text:
                q_type, section_title, instruction = get_section_info(q_num)
                q["content"]["text"] = f"{instruction}\n\n{q_text}"

            questions.append(q)

    return questions


def extract_question_text_from_full(full_text: str, q_num: int) -> Optional[str]:
    """
    Extract the text for a specific question from the full PDF text.
    """
    # Look for question number followed by content until next question number
    # Pattern: starts with number, ends before next number
    pattern = rf'\n{q_num}\s*\n(.+?)(?=\n{q_num + 1}\s*\n|\n--- PAGE|\Z)'

    match = re.search(pattern, full_text, re.DOTALL)
    if match:
        content = match.group(1).strip()
        # Clean up the content
        content = re.sub(r'\s+', ' ', content)
        # Remove page markers
        content = re.sub(r'Page \d+.*?>>>', '', content)
        content = re.sub(r'Please go on to the next page', '', content)
        return content[:500] if len(content) > 500 else content

    return None


def extract_question_content_detailed(
    extractor: VectorExtractor,
    page_idx: int,
    q_num: int,
    q_top: float,
    next_q_top: Optional[float],
    words: list[dict]
) -> str:
    """
    Extract the actual question content (words, numbers, etc.) from the page.
    """
    page_height = extractor.get_page_dimensions(page_idx)[1]

    # Define the region above the question number (where the question content is)
    # The question number appears at the bottom of the question block
    region_bottom = q_top + 20  # Include some margin below the number

    # Find the region top - either the previous question or reasonable margin above
    if next_q_top is not None and next_q_top < q_top:
        # Previous question is above on same page
        region_top = next_q_top + 40
    else:
        # Estimate based on typical question height
        region_top = max(50, q_top - 150)

    # Get words in this region
    region_words = [
        w for w in words
        if region_top < float(w['top']) < region_bottom
        and float(w['x0']) > 80  # Exclude left margin
    ]

    # Sort by position (top to bottom, left to right)
    region_words.sort(key=lambda w: (float(w['top']), float(w['x0'])))

    # Combine words into text, preserving line breaks
    if not region_words:
        return ""

    lines = []
    current_line = []
    last_top = None

    for w in region_words:
        top = float(w['top'])
        text = w['text'].strip()

        if not text:
            continue

        # Skip option letters and common markers
        if text in ['A', 'B', 'C', 'D', 'E'] and float(w['x0']) < 150:
            continue

        if last_top is None or abs(top - last_top) < 15:
            # Same line
            current_line.append(text)
        else:
            # New line
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [text]

        last_top = top

    if current_line:
        lines.append(' '.join(current_line))

    # Join lines and clean up
    content = '\n'.join(lines)

    # Clean up common artifacts
    content = re.sub(r'\s+', ' ', content)
    content = content.strip()

    return content[:300] if len(content) > 300 else content


def parse_vr_booklet_detailed(booklet_path: Path, booklet_num: int, answers: dict[int, str]) -> list[dict]:
    """
    Parse a VR test booklet with detailed question extraction.
    """
    questions = []

    with VectorExtractor(booklet_path) as extractor:
        print(f"\nProcessing {booklet_path.name}")

        # Build mapping of question positions across pages
        q_locations = {}  # {q_num: (page_idx, top_y)}
        page_words_cache = {}  # {page_idx: words}

        for page_idx in range(extractor.page_count):
            words = extractor.extract_words(page_idx)
            page_words_cache[page_idx] = words

            # Find question numbers in left margin
            for w in words:
                if w['text'].isdigit():
                    num = int(w['text'])
                    if 1 <= num <= 80 and float(w['x0']) < 70:
                        if num not in q_locations:
                            q_locations[num] = (page_idx, float(w['top']))

        print(f"Found {len(q_locations)} question locations")

        # Extract text for each question
        for q_num, answer in sorted(answers.items()):
            # Get section info for question type
            q_type, section_title, instruction = get_section_info(q_num)

            # Build the basic question
            q = build_question(q_num, answer, booklet_num, booklet_path.name)

            if q_num in q_locations:
                page_idx, q_top = q_locations[q_num]
                words = page_words_cache.get(page_idx, [])

                # Find the previous question's position on the same page (if any)
                prev_q_top = None
                for prev_num in range(q_num - 1, 0, -1):
                    if prev_num in q_locations:
                        prev_page, prev_top = q_locations[prev_num]
                        if prev_page == page_idx:
                            prev_q_top = prev_top
                            break

                # Extract actual question content
                content = extract_question_content_detailed(
                    extractor, page_idx, q_num, q_top, prev_q_top, words
                )

                if content:
                    q["content"]["text"] = f"Q{q_num}. {instruction}\n\n{content}"
                else:
                    q["content"]["text"] = f"Q{q_num}. {instruction}"
            else:
                q["content"]["text"] = f"Q{q_num}. {instruction}"

            questions.append(q)

    return questions


def main():
    """Main extraction function."""
    print("GL Verbal Reasoning Extraction")
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

    # Extract all answers first
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

        print(f"\n2. Processing Booklet {booklet_num}...")
        answers = all_answers[booklet_num]

        questions = parse_vr_booklet_detailed(booklet_path, booklet_num, answers)
        all_questions.extend(questions)

        print(f"   Extracted {len(questions)} questions from Booklet {booklet_num}")

    # Save to JSON
    print(f"\n3. Saving {len(all_questions)} questions to {OUTPUT_JSON}")
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(all_questions, f, indent=2)

    # Print summary by type
    print("\n4. Summary by question type:")
    type_counts = {}
    for q in all_questions:
        qt = q['question_type']
        type_counts[qt] = type_counts.get(qt, 0) + 1

    for qt, count in sorted(type_counts.items()):
        print(f"   {qt}: {count}")

    print(f"\nTotal: {len(all_questions)} VR questions extracted")


if __name__ == "__main__":
    main()
