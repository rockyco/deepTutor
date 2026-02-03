"""Extract questions from local sample PDFs.

Processes PDFs in /samples/ directory:
- English/1/ : GL English Familiarisation 1 (test booklet + parent guide)
- English/2/ : CGP 11+ English Sample Paper (test + mark scheme)
- English/words/ : 550-word vocabulary list -> vocabulary_550.json
- VR/1/ : 11pluscentre.co.uk VR Paper 2 (letter series, answer sheet is image-based)
- VR/2/ : GL VR Familiarisation 1-3 (test booklets + parent guide)
- NVR/ : Skipped (image-based questions, not reliably extractable as text)

Output:
- backend/data/questions/sample_pdfs.json  (question bank format)
- backend/data/lessons/vocabulary_550.json (vocabulary list)

Usage:
    cd backend && uv run python scripts/extract_sample_pdfs.py
"""

import json
import re
import sys
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber not installed. Run: uv pip install pdfplumber")
    sys.exit(1)

# fitz (PyMuPDF) is available in the project but not needed for text extraction.
# It would be used if we needed to extract images from PDFs.


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLES_DIR = PROJECT_ROOT / "samples"
OUTPUT_QUESTIONS = PROJECT_ROOT / "backend" / "data" / "questions" / "sample_pdfs.json"
OUTPUT_VOCAB = PROJECT_ROOT / "backend" / "data" / "lessons" / "vocabulary_550.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def pdf_text_pages(path: Path) -> list[str]:
    """Extract text from each page of a PDF using pdfplumber."""
    pages = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return pages


def pdf_text_all(path: Path) -> str:
    """Extract all text from a PDF as one string."""
    return "\n".join(pdf_text_pages(path))


def make_question(
    subject: str,
    question_type: str,
    text: str,
    options: list[str],
    answer_value: str,
    explanation: str = "",
    source: str = "gl_sample_pdf",
    tags: list[str] | None = None,
    passage: str | None = None,
    difficulty: int = 3,
) -> dict:
    """Build a question dict in deployment_dump.json format."""
    content = {"text": text}
    if options:
        content["options"] = options
    if passage:
        content["passage"] = passage

    return {
        "subject": subject,
        "question_type": question_type,
        "format": "multiple_choice" if options else "fill_in_blank",
        "difficulty": difficulty,
        "content": content,
        "answer": {"value": answer_value},
        "explanation": explanation,
        "hints": [],
        "tags": tags or ["gl_sample"],
        "source": source,
    }


# ---------------------------------------------------------------------------
# English 1: GL Familiarisation (test booklet + parent guide)
# ---------------------------------------------------------------------------


def parse_gl_english_answer_key(parent_guide_path: Path) -> dict[str, dict[int, str]]:
    """Parse answer keys from English Parent's Guide.

    Returns {"1": {1: "B", 2: "C", ...}, "2": {1: "D", ...}}
    """
    pages = pdf_text_pages(parent_guide_path)
    all_answers = {}

    for page_text in pages:
        # Detect "English Familiarisation N" header
        fam_match = re.search(
            r"English\s+Familiarisation\s+(\d+)", page_text, re.IGNORECASE
        )
        if not fam_match:
            continue

        label = fam_match.group(1)
        answers = {}

        # Parse "N. X" patterns (answer number dot letter/N)
        # The layout is multi-column so lines interleave
        for m in re.finditer(r"(\d{1,2})\.\s+([A-EN])\b", page_text):
            qnum = int(m.group(1))
            ans = m.group(2)
            if qnum not in answers:
                answers[qnum] = ans

        if answers:
            all_answers[label] = answers

    return all_answers


def extract_gl_english_1(booklet_path: Path, answers: dict[int, str]) -> list[dict]:
    """Extract questions from GL English Familiarisation 1 test booklet."""
    questions = []
    pages = pdf_text_pages(booklet_path)

    # --- Passage extraction (pages 1-2 typically) ---
    passage_lines = []
    question_pages_text = []
    in_questions = False

    for i, text in enumerate(pages):
        if i == 0:
            # Instruction page
            continue

        # Question pages have numbered questions with A-E options
        has_numbered_q = bool(re.search(r"^\d{1,2}\s+", text, re.MULTILINE))
        has_options = bool(re.search(r"^[A-E]\s+\w", text, re.MULTILINE))

        if has_numbered_q and has_options:
            in_questions = True

        if in_questions:
            question_pages_text.append(text)
        elif i >= 1 and not in_questions:
            # Passage pages - before questions start
            passage_lines.append(text)

    passage_text = "\n".join(passage_lines)
    # Clean passage: remove line numbers, page markers
    passage_text = re.sub(r"^\d+\.\s*$", "", passage_text, flags=re.MULTILINE)
    passage_text = re.sub(r"Page\s+\d+.*$", "", passage_text, flags=re.MULTILINE)
    passage_text = re.sub(r"Please go on.*$", "", passage_text, flags=re.MULTILINE)
    passage_text = re.sub(r"\n{3,}", "\n\n", passage_text).strip()

    # --- Question extraction ---
    all_question_text = "\n".join(question_pages_text)

    # Split by question numbers: "N text" at start of line
    # English GL format: question number, then question text, then A-E options on separate lines
    q_blocks = _parse_english_question_blocks(all_question_text)

    # Detect section boundaries for question type classification
    section_starts = _detect_english_sections(all_question_text, pages)

    for qnum in sorted(answers.keys()):
        answer_val = answers[qnum]
        block = q_blocks.get(qnum)

        if block is None:
            continue

        q_text, options = block
        if not q_text or q_text == f"Question {qnum}":
            continue

        # Classify question type based on section
        qtype = _classify_english_question(qnum, q_text, section_starts)

        # Determine if this is a comprehension question (needs passage)
        is_comprehension = qtype == "comprehension"

        # Resolve answer value to option text
        answer_text = _resolve_answer_letter(answer_val, options)

        explanation = f"The correct answer is {answer_val}."
        q = make_question(
            subject="english",
            question_type=qtype,
            text=q_text,
            options=options,
            answer_value=answer_text,
            explanation=explanation,
            source="gl_sample_pdf",
            tags=["gl_sample", "gl_english_1"],
            passage=passage_text if is_comprehension else None,
        )
        questions.append(q)

    return questions


def _parse_english_question_blocks(text: str) -> dict[int, tuple[str, list[str]]]:
    """Parse English question blocks into {qnum: (question_text, [options])}.

    Handles GL format where:
    - Question number appears at start of line or standalone
    - Question text follows (may span multiple lines)
    - Options A through E on separate lines: "A option_text"
    """
    blocks = {}
    lines = text.split("\n")
    current_q = None
    current_parts = []
    current_options = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "Please go on" in line or line.startswith("Page "):
            continue

        # Standalone question number
        if re.match(r"^\d{1,2}$", line):
            candidate = int(line)
            if 1 <= candidate <= 100:
                if current_q is not None:
                    blocks[current_q] = (
                        " ".join(current_parts).strip(),
                        current_options,
                    )
                current_q = candidate
                current_parts = []
                current_options = []
                continue

        # "N question text" pattern
        m = re.match(r"^(\d{1,2})\s+(.+)$", line)
        if m:
            candidate = int(m.group(1))
            if 1 <= candidate <= 100:
                if current_q is not None:
                    blocks[current_q] = (
                        " ".join(current_parts).strip(),
                        current_options,
                    )
                current_q = candidate
                current_parts = [m.group(2)]
                current_options = []
                continue

        if current_q is not None:
            # Option line: "A some text"
            opt_match = re.match(r"^([A-E])\s+(.+)$", line)
            if opt_match:
                current_options.append(opt_match.group(2).strip())
            elif line == "N":
                # "N" means "None of these" / no mistake
                current_options.append("None of these")
            else:
                current_parts.append(line)

    if current_q is not None:
        blocks[current_q] = (" ".join(current_parts).strip(), current_options)

    return blocks


def _detect_english_sections(
    all_text: str, pages: list[str]
) -> dict[str, tuple[int, int]]:
    """Detect section boundaries in English paper.

    Returns {section_name: (first_qnum, last_qnum)}.
    """
    sections = {}

    # Check full page text for section transitions
    for page_text in pages:
        if re.search(r"Spelling\s+Exercise", page_text, re.IGNORECASE):
            # Find first question number on this page
            first_q = re.search(r"^\s*(\d{1,2})\s", page_text, re.MULTILINE)
            if first_q:
                sections["spelling"] = int(first_q.group(1))
        if re.search(r"Hippos|Punctuation", page_text, re.IGNORECASE):
            first_q = re.search(r"^\s*(\d{1,2})\s", page_text, re.MULTILINE)
            if first_q:
                sections["punctuation"] = int(first_q.group(1))
        if re.search(r"Performance Time|choose the best word", page_text, re.IGNORECASE):
            first_q = re.search(r"^\s*(\d{1,2})\s", page_text, re.MULTILINE)
            if first_q:
                sections["grammar"] = int(first_q.group(1))

    return sections


def _classify_english_question(
    qnum: int, text: str, sections: dict[str, int]
) -> str:
    """Classify an English question type based on its number and content."""
    spelling_start = sections.get("spelling", 29)
    punctuation_start = sections.get("punctuation", 38)
    grammar_start = sections.get("grammar", 47)

    if qnum < spelling_start:
        return "comprehension"
    elif qnum < punctuation_start:
        return "spelling"
    elif qnum < grammar_start:
        return "punctuation"
    else:
        return "grammar"


def _resolve_answer_letter(letter: str, options: list[str]) -> str:
    """Convert answer letter (A-E or N) to option text."""
    if letter == "N":
        # Look for "None of these" in options
        for opt in options:
            if "none" in opt.lower() or "no mistake" in opt.lower():
                return opt
        return "None of these"

    letter_idx = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
    idx = letter_idx.get(letter.upper())
    if idx is not None and idx < len(options):
        return options[idx]
    return letter


# ---------------------------------------------------------------------------
# English 2: CGP 11+ English Sample Paper
# ---------------------------------------------------------------------------


def extract_cgp_english(booklet_path: Path, mark_scheme_path: Path) -> list[dict]:
    """Extract questions from CGP 11+ English Sample Paper.

    Uses the mark scheme for correct answers and explanations.
    """
    questions = []

    # Parse mark scheme for answers and explanations
    answers_with_explanations = _parse_cgp_mark_scheme(mark_scheme_path)

    # Parse test booklet for questions
    pages = pdf_text_pages(booklet_path)

    # Extract passages
    passage_1 = _extract_cgp_passage(pages, 0, "The Crystal Heart")
    passage_2 = _extract_cgp_passage(pages, 3, "The Secret Garden")

    # Parse question blocks from all pages
    q_blocks = _parse_cgp_question_blocks(pages)

    for qnum in sorted(answers_with_explanations.keys()):
        answer_letter, explanation = answers_with_explanations[qnum]
        block = q_blocks.get(qnum)

        if block is None:
            continue

        q_text, options = block
        if not q_text:
            continue

        # Classify question type
        qtype = _classify_cgp_english_question(qnum, q_text)

        # Determine passage
        passage = None
        if qnum <= 14:
            passage = passage_1
        elif 15 <= qnum <= 28:
            passage = passage_2

        # Resolve answer
        answer_text = _resolve_answer_letter(answer_letter, options)

        q = make_question(
            subject="english",
            question_type=qtype,
            text=q_text,
            options=options,
            answer_value=answer_text,
            explanation=explanation,
            source="cgp_sample_pdf",
            tags=["cgp_sample", "cgp_english"],
            passage=passage,
        )
        questions.append(q)

    return questions


def _parse_cgp_mark_scheme(path: Path) -> dict[int, tuple[str, str]]:
    """Parse CGP mark scheme. Returns {qnum: (answer_letter, explanation)}."""
    text = pdf_text_all(path)
    results = {}

    # The mark scheme has entries like:
    # "1) B - Mi Nuong is lonely because..."
    # Split by question number pattern
    for m in re.finditer(
        r"(\d{1,2})\)\s+([A-EN])\s*[-\u2014]\s*(.+?)(?=\d{1,2}\)\s+[A-EN]\s*[-\u2014]|$)",
        text,
        re.DOTALL,
    ):
        qnum = int(m.group(1))
        letter = m.group(2)
        explanation = m.group(3).strip()
        # Clean up multi-line explanations
        explanation = re.sub(r"\s+", " ", explanation).strip()
        results[qnum] = (letter, explanation)

    return results


def _extract_cgp_passage(pages: list[str], start_page: int, title: str) -> str:
    """Extract a named passage from CGP English paper."""
    passage_lines = []
    collecting = False

    for i, text in enumerate(pages):
        if title in text:
            collecting = True
            # Get text after the title line
            lines = text.split("\n")
            for j, line in enumerate(lines):
                if title in line:
                    passage_lines.extend(lines[j + 1 :])
                    break
            continue

        if collecting:
            # Stop when we hit questions (numbered with options)
            if re.search(r"^\d{1,2}\.\s+", text, re.MULTILINE):
                break
            passage_lines.append(text)

    passage = "\n".join(passage_lines)
    # Clean up
    passage = re.sub(r"Page\s+\d+", "", passage)
    passage = re.sub(r"Please go on.*", "", passage)
    passage = re.sub(r"^\d+\s*$", "", passage, flags=re.MULTILINE)
    passage = re.sub(r"\n{3,}", "\n\n", passage).strip()
    return passage


def _parse_cgp_question_blocks(
    pages: list[str],
) -> dict[int, tuple[str, list[str]]]:
    """Parse CGP-format questions.

    CGP format uses:
    - "N. question text" for comprehension
    - Lettered options on separate lines: "A option_text"
    - Spelling/punctuation with inline options
    - Grammar with inline options separated by spaces
    """
    blocks = {}

    for page_text in pages:
        lines = page_text.split("\n")
        current_q = None
        current_parts = []
        current_options = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("Sample 11+"):
                continue
            if line.startswith("Allow 50"):
                continue
            if "answer sheet" in line.lower():
                continue
            if "Please go on" in line or line.startswith("Page "):
                continue
            if line.startswith("Answer these"):
                continue

            # CGP uses "N." format for question numbers
            m = re.match(r"^(\d{1,2})\.\s+(.+)$", line)
            if m:
                candidate = int(m.group(1))
                if 1 <= candidate <= 60:
                    if current_q is not None:
                        blocks[current_q] = (
                            " ".join(current_parts).strip(),
                            current_options,
                        )
                    current_q = candidate
                    current_parts = [m.group(2)]
                    current_options = []
                    continue

            # Standalone question number (for spelling/punctuation)
            if re.match(r"^(\d{1,2})\.$", line) or re.match(r"^(\d{1,2})$", line):
                m2 = re.match(r"^(\d{1,2})", line)
                candidate = int(m2.group(1))
                if 1 <= candidate <= 60:
                    if current_q is not None:
                        blocks[current_q] = (
                            " ".join(current_parts).strip(),
                            current_options,
                        )
                    current_q = candidate
                    current_parts = []
                    current_options = []
                    continue

            if current_q is not None:
                # CGP option: "A text" on its own line
                opt_match = re.match(r"^([A-E])\s+(.+)$", line)
                if opt_match:
                    current_options.append(opt_match.group(2).strip())
                elif line == "N":
                    current_options.append("No mistake")
                else:
                    current_parts.append(line)

        if current_q is not None:
            blocks[current_q] = (" ".join(current_parts).strip(), current_options)

    # Post-process: for spelling/grammar questions, try to extract inline options
    for qnum in list(blocks.keys()):
        text, options = blocks[qnum]
        if not options and qnum >= 29:
            # Spelling questions have A B C D markers inline
            # Grammar questions have options separated by spaces
            inline_opts = _extract_inline_options(text)
            if inline_opts:
                clean_text = _remove_inline_options(text, inline_opts)
                blocks[qnum] = (clean_text, inline_opts)

    return blocks


def _extract_inline_options(text: str) -> list[str]:
    """Try to extract inline A B C D (E) options from text."""
    # Pattern for grammar-style: "word1 word2 word3 word4 word5" with separators
    # These are hard to parse generically - return empty for now
    return []


def _remove_inline_options(text: str, options: list[str]) -> str:
    """Remove inline options from question text."""
    for opt in options:
        text = text.replace(opt, "")
    return re.sub(r"\s+", " ", text).strip()


def _classify_cgp_english_question(qnum: int, text: str) -> str:
    """Classify CGP English question type."""
    if qnum <= 14:
        return "comprehension"
    elif qnum <= 28:
        return "comprehension"
    elif qnum <= 37:
        return "spelling"
    elif qnum <= 40:
        return "punctuation"
    elif qnum <= 50:
        return "grammar"
    else:
        return "grammar"


# ---------------------------------------------------------------------------
# VR: GL Familiarisation 1-3 (test booklets + parent guide)
# ---------------------------------------------------------------------------


def parse_gl_vr_answer_key(parent_guide_path: Path) -> dict[str, dict[int, str]]:
    """Parse answer keys from VR Parent's Guide.

    The VR answer keys are dense multi-column layouts with mixed answer types:
    - Single letters (t, r, b, ...)
    - Words (map, tan, hit, ...)
    - Phrases (hit, miss / cheap, dear)
    - Numbers (23, 22, ...)
    - Letter pairs (YL, NC, ...)
    - Multi-word (not alerted, shampoo left, ...)

    Returns {"1": {1: "t", 2: "r", ...}, "2": {...}, "3": {...}}
    """
    pages = pdf_text_pages(parent_guide_path)
    all_answers = {}

    for page_text in pages:
        # Detect "Verbal Reasoning Familiarisation N"
        fam_match = re.search(
            r"Verbal\s+Reasoning\s+Familiarisation\s+(\d+)",
            page_text,
            re.IGNORECASE,
        )
        if not fam_match:
            continue

        label = fam_match.group(1)
        answers = {}

        # Parse answer lines: "N. answer_text"
        # These may appear across multiple columns
        for m in re.finditer(r"(\d{1,2})\.\s+(.+?)(?=\s+\d{1,2}\.\s|\n|$)", page_text):
            qnum = int(m.group(1))
            ans = m.group(2).strip()
            # Clean up: remove trailing content that's not part of the answer
            ans = re.sub(r"\s*Page\s+\d+.*$", "", ans)
            ans = re.sub(r"\s*Section\s+\d+.*$", "", ans)
            if qnum not in answers and ans:
                answers[qnum] = ans

        if answers:
            all_answers[label] = answers

    return all_answers


def extract_gl_vr_booklet(
    booklet_path: Path, answers: dict[int, str], booklet_num: int
) -> list[dict]:
    """Extract VR questions from a GL Familiarisation booklet.

    Strategy: Parse page-by-page. Track the current section instruction.
    For each question number found, collect its text and options.
    VR questions have many formats so we keep the raw question text
    and match with answer keys.
    """
    questions = []
    pages = pdf_text_pages(booklet_path)

    # Parse all questions from all pages
    current_instruction = ""
    current_section_type = "mixed"
    all_parsed = []  # [(qnum, text, options, instruction, section_type)]

    # Track section context

    for page_idx, page_text in enumerate(pages):
        if page_idx == 0:
            # Instruction cover page
            continue

        lines = page_text.split("\n")

        # Check if this page has a new section instruction
        new_instruction = _detect_vr_instruction(page_text)
        if new_instruction:
            current_instruction = new_instruction
            current_section_type = _classify_vr_section(current_instruction)
            # Example typically follows instruction

        # Parse questions from this page
        page_questions = _parse_vr_page_questions(
            lines, current_instruction, current_section_type
        )

        for qnum, q_text, q_options in page_questions:
            all_parsed.append(
                (qnum, q_text, q_options, current_instruction, current_section_type)
            )

    # Build output questions, matching with answer keys
    for qnum, q_text, q_options, instruction, section_type in all_parsed:
        answer_val = answers.get(qnum, "")
        if not answer_val:
            continue

        # Build full question text
        full_text = q_text.strip()
        if not full_text:
            continue

        # For option-based questions, resolve answer to option text
        if q_options and answer_val.upper() in "ABCDE" and len(answer_val) == 1:
            answer_text = _resolve_answer_letter(answer_val, q_options)
        else:
            answer_text = answer_val

        q = make_question(
            subject="verbal_reasoning",
            question_type=f"vr_{section_type}",
            text=full_text,
            options=q_options,
            answer_value=answer_text,
            explanation=f"The correct answer is {answer_val}.",
            source="gl_sample_pdf",
            tags=["gl_sample", f"gl_vr_{booklet_num}"],
        )
        questions.append(q)

    return questions


def _detect_vr_instruction(page_text: str) -> str:
    """Detect if a page starts a new VR section with instruction text.

    Returns the instruction text, or empty string if none found.
    """
    # VR section instructions typically start with patterns like:
    # "In this question, one letter can be moved..."
    # "In these questions, find two words..."
    # "Read the following information..."
    # "Three of these four words are given in code."
    # "The alphabet is here to help you..."

    patterns = [
        r"(In (?:this|these|each) question[s,].*?(?:answer sheet\.))",
        r"(In these sentences,.*?(?:answer sheet\.))",
        r"(Read the following information.*?(?:answer sheet\.))",
        r"(Three of these four words.*?(?:answer sheet\.))",
        r"(In these questions,.*?(?:answer sheet\.))",
        r"(The alphabet is here.*?(?:answer sheet\.))",
        r"(Find the (?:next|two|letter|number|word).*?(?:answer sheet\.))",
    ]

    for pattern in patterns:
        m = re.search(pattern, page_text, re.DOTALL | re.IGNORECASE)
        if m:
            instruction = m.group(1).strip()
            # Clean up: collapse whitespace
            instruction = re.sub(r"\s+", " ", instruction)
            return instruction

    return ""


def _classify_vr_section(instruction: str) -> str:
    """Classify VR section type from instruction text."""
    inst = instruction.lower()

    if "letter" in inst and "move" in inst:
        return "letter_move"
    if "bracket" in inst and "letter" in inst:
        return "missing_letter"
    if "same way" in inst or "second group" in inst or "missing in the second" in inst:
        return "word_analogies"
    if "number" in inst and ("series" in inst or "continue" in inst):
        return "number_series"
    if "opposite" in inst:
        return "antonyms"
    if "similar" in inst or "closest in meaning" in inst or "nearest" in inst:
        return "synonyms"
    if "hidden" in inst:
        return "hidden_word"
    if "code" in inst or "three of these four words" in inst:
        return "codes"
    if "alphabet" in inst or "pair of letters" in inst or "next pair" in inst:
        return "letter_series"
    if "capital" in inst and "three letters" in inst:
        return "missing_three_letters"
    if "complete the sentence" in inst or "equally well" in inst:
        return "double_meaning"
    if "read the following information" in inst:
        return "logic"

    return "mixed"


def _parse_vr_page_questions(
    lines: list[str], instruction: str, section_type: str
) -> list[tuple[int, str, list[str]]]:
    """Parse VR questions from a single page's lines.

    Returns [(qnum, question_text, [options]), ...]
    """
    questions = []
    current_q = None
    current_parts = []
    current_options = []
    skip_until_next_q = False

    # Lines to skip
    skip_patterns = [
        "Please go on",
        "Example",
        "Solution",
        "Answer ",
        "Page ",
        "A B C D E F G H I J K L M N O P Q R S T U V W X Y Z",
        "Copyright",
        "Read the following with",
    ]

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1

        if not line:
            continue

        # Skip known non-question lines
        should_skip = False
        for sp in skip_patterns:
            if line.startswith(sp) or sp in line:
                should_skip = True
                # "Example" or "Solution" means we're in example block
                if "Example" in line or "Solution" in line:
                    skip_until_next_q = True
                break
        if should_skip:
            continue

        # Skip instruction text (already captured)
        if line.startswith("In this ") or line.startswith("In these "):
            skip_until_next_q = True
            continue
        if line.startswith("Find the letter") or line.startswith("Find this letter"):
            skip_until_next_q = True
            continue
        if line.startswith("Mark ") or line.startswith("The letters must"):
            continue
        if line.startswith("Three of these"):
            skip_until_next_q = True
            continue
        if line.startswith("Read the following"):
            skip_until_next_q = True
            continue

        # Check for question number at start of line
        m = re.match(r"^(\d{1,3})\s+(.*)$", line)
        if m and 1 <= int(m.group(1)) <= 200:
            candidate = int(m.group(1))
            # Save previous question
            if current_q is not None:
                q_text = " ".join(current_parts).strip()
                questions.append((current_q, q_text, current_options))

            skip_until_next_q = False
            current_q = candidate
            rest = m.group(2).strip()
            current_parts = []
            current_options = []

            # Try to parse options from the rest of the line
            # Pattern: "A x B y C z D w E v" (single-word options)
            opt_match = re.findall(r"\b([A-E])\s+(\S+)", rest)
            if len(opt_match) == 5:
                current_options = [o[1] for o in opt_match]
                # Remove options from question text
                clean = rest
                for letter, val in opt_match:
                    clean = clean.replace(f"{letter} {val}", "", 1)
                clean = clean.strip()
                if clean:
                    current_parts = [clean]
            else:
                current_parts = [rest] if rest else []
            continue

        # Standalone question number
        if re.match(r"^\d{1,3}$", line):
            candidate = int(line)
            if 1 <= candidate <= 200:
                if current_q is not None:
                    q_text = " ".join(current_parts).strip()
                    questions.append((current_q, q_text, current_options))
                skip_until_next_q = False
                current_q = candidate
                current_parts = []
                current_options = []
                continue

        if skip_until_next_q:
            continue

        if current_q is not None:
            # Check for multi-option line FIRST: "A x B y C z D w E v"
            # This catches lines like "A m B t C d D s E n"
            multi_opts = re.findall(r"\b([A-E])\s+(\S+)", line)
            if len(multi_opts) >= 4 and line[0] in "ABCDE":
                current_options = [o[1] for o in multi_opts[:5]]
                continue

            # Multi-option with X/Y/Z format (for antonyms/analogies):
            # "A word1 X word4"
            multi_opt_xyz = re.match(
                r"^([A-C])\s+(\S+)\s+([X-Z])\s+(\S+)$", line
            )
            if multi_opt_xyz:
                current_options.append(
                    f"{multi_opt_xyz.group(2)} / {multi_opt_xyz.group(4)}"
                )
                continue

            # Single option: "A text" (but NOT if it looks like multi-option)
            single_opt = re.match(r"^([A-E])\s+(.+)$", line)
            if single_opt:
                current_options.append(single_opt.group(2).strip())
                continue

            # Continuation of question text
            current_parts.append(line)

    # Save last question
    if current_q is not None:
        q_text = " ".join(current_parts).strip()
        questions.append((current_q, q_text, current_options))

    return questions


# ---------------------------------------------------------------------------
# VR: 11pluscentre Paper 2 (letter series)
# ---------------------------------------------------------------------------


def extract_vr_paper2(booklet_path: Path) -> list[dict]:
    """Extract VR Paper 2 (letter series) from 11pluscentre.

    This paper has 24 letter-series questions with 5 options each.
    The answer sheet is on the last page of the booklet.
    The separate "Paper 2 Answers.pdf" is image-only (scanned), so we skip it.
    """
    questions = []
    pages = pdf_text_pages(booklet_path)

    # Parse questions from pages 2-5 (pages with question grids)
    for page_text in pages:
        # Match patterns like: "1 CP DO FN IM ML [ __ ]"
        # followed by 5 options on next lines
        lines = page_text.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Match question line: "N  AB CD EF GH IJ [ __ ]"
            q_match = re.match(
                r"^(\d{1,2})\s+([A-Z]{2}(?:\s+[A-Z]{2})+)\s+\[.*\]",
                line,
            )
            if q_match:
                series = q_match.group(2).strip()

                # Collect options from following lines
                options = []
                j = i + 1
                while j < len(lines) and len(options) < 5:
                    opt_line = lines[j].strip()
                    if not opt_line:
                        j += 1
                        continue
                    # Options are letter pairs, possibly multiple per line
                    pairs = re.findall(r"\b([A-Z]{2})\b", opt_line)
                    if pairs:
                        options.extend(pairs)
                    else:
                        break
                    j += 1

                if options:
                    options = options[:5]
                    q_text = f"Find the letters that best complete the series: {series} [ ? ]"
                    q = make_question(
                        subject="verbal_reasoning",
                        question_type="vr_letter_series",
                        text=q_text,
                        options=options,
                        answer_value="",  # We don't have reliable answers
                        explanation="",
                        source="11pluscentre_sample_pdf",
                        tags=["11pluscentre_sample", "vr_letter_series"],
                    )
                    questions.append(q)

            i += 1

    return questions


# ---------------------------------------------------------------------------
# Vocabulary: 550words.pdf
# ---------------------------------------------------------------------------


def extract_vocabulary(vocab_path: Path) -> list[dict]:
    """Extract vocabulary words and definitions from 550words.pdf.

    The PDF has two layout formats for entries:
    1. Single-line: "Word Definition text on same line"
       e.g. "Abundance A large amount of something..."
    2. Multi-line: definition wraps around the word
       e.g. "The place someone calls home..."  (definition start)
            "Abode"                              (word on its own line)
            "and could be any type..."           (definition continuation)

    Returns list of {word, definition} dicts.
    """
    pages = pdf_text_pages(vocab_path)

    # Words that are NOT vocabulary entries (common sentence starters)
    not_words = {
        "Word", "Definition", "The", "This", "Something", "Having", "Being",
        "An", "To", "Dry", "Feeling", "Sticking", "Someone", "Collect",
        "Being", "Reduced", "Not", "Well", "Page", "Showing", "Very",
        "Stating", "Despite", "Due", "Nothing", "Can", "Could", "Would",
        "Should", "May", "Might", "What", "Where", "When", "How", "Why",
    }

    # First pass: collect all lines, identify words vs definition text
    entries = []  # [(word, definition)]

    for page_text in pages:
        lines = page_text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if "11+ 500 Words" in line:
                continue
            if line.startswith("Word Definition"):
                continue
            if re.match(r"^Page \d+ of \d+$", line):
                continue

            # Check for single-line format: "Word Definition text"
            m = re.match(r"^([A-Z][a-z]+)\s+(.+)$", line)
            if m:
                word_candidate = m.group(1)
                rest = m.group(2)

                if word_candidate not in not_words and len(word_candidate) >= 3:
                    # This is a word with inline definition
                    entries.append(("WORD", word_candidate, rest))
                    continue

            # Check for standalone word (multi-line format)
            if re.match(r"^[A-Z][a-z]+$", line) and line not in not_words and len(line) >= 3:
                entries.append(("WORD_STANDALONE", line, ""))
                continue

            # Otherwise it's definition text (continuation or pre-word)
            entries.append(("DEF_TEXT", "", line))

    # Second pass: assign definitions to words
    # For WORD_STANDALONE entries, the definition wraps around the word:
    #   [pre-def lines]
    #   WordStandalone
    #   [post-def lines]
    # For WORD entries, definition starts inline and may continue on next lines.
    #
    # The tricky part is splitting DEF_TEXT runs between consecutive standalone words.
    # Between two standalone words, DEF_TEXT lines may belong to word A (post-def)
    # or word B (pre-def). We use the heuristic that a sentence ending with "."
    # marks the boundary: text before the period-ending line is post-def of A,
    # text after is pre-def of B.

    word_indices = [
        i for i, (tag, _, _) in enumerate(entries) if tag.startswith("WORD")
    ]

    vocab = []
    for wi, idx in enumerate(word_indices):
        tag, word, inline_text = entries[idx]
        next_word_idx = (
            word_indices[wi + 1] if wi + 1 < len(word_indices) else len(entries)
        )
        prev_word_idx = word_indices[wi - 1] if wi > 0 else -1

        if tag == "WORD":
            # Inline definition + continuation until next word entry
            def_parts = [inline_text]
            for j in range(idx + 1, next_word_idx):
                jtag = entries[j][0]
                if jtag == "DEF_TEXT":
                    def_parts.append(entries[j][2])
                elif jtag == "WORD_STANDALONE":
                    # The remaining DEF_TEXT before this standalone belongs to it
                    break
                else:
                    break

        elif tag == "WORD_STANDALONE":
            # For standalone words, the definition is split:
            #   [pre-def lines]   <- definition start (before word)
            #   StandaloneWord
            #   [post-def lines]  <- definition continuation (after word)
            #
            # Between two consecutive standalone words, all DEF_TEXT lines
            # must be split: some belong to word A (post-def), some to word B (pre-def).
            # Heuristic: post-def lines start with lowercase (continuation),
            # pre-def lines start with uppercase or a capital (new sentence = new def).

            # Collect ALL DEF_TEXT between previous word entry and this one
            between_texts = []
            for k in range(prev_word_idx + 1, idx):
                if entries[k][0] == "DEF_TEXT":
                    between_texts.append((k, entries[k][2]))

            # Split between_texts: find where the previous word's definition ends
            # and this word's definition begins.
            # Approach: scan from the end backward; lines that start with lowercase
            # or look like continuations stay as pre-def. Lines before that are post-def
            # of previous word.
            split_point = 0  # default: all belong to this word's pre-def
            for si in range(len(between_texts)):
                line_text = between_texts[si][1]
                # If this line starts with uppercase and the previous line ends with "."
                # it's likely the start of a new definition
                if si > 0 and line_text and line_text[0].isupper():
                    prev_line = between_texts[si - 1][1]
                    if prev_line.rstrip().endswith((".","!", "?")):
                        split_point = si
                        break

            pre_def = [t for _, t in between_texts[split_point:]]

            # Trim previous word's definition to exclude pre_def lines
            if vocab and split_point < len(between_texts):
                prev_def = vocab[-1]["definition"]
                for _, pd_text in between_texts[split_point:]:
                    pd_stripped = pd_text.strip()
                    if pd_stripped and pd_stripped in prev_def:
                        cut_idx = prev_def.find(pd_stripped)
                        prev_def = prev_def[:cut_idx].strip()
                vocab[-1]["definition"] = prev_def

            # Collect post-def: DEF_TEXT immediately after this word
            post_def = []
            for j in range(idx + 1, next_word_idx):
                if entries[j][0] == "DEF_TEXT":
                    text_line = entries[j][2]
                    # Stop if this looks like a new definition start
                    # (starts with uppercase and previous line ended with period)
                    if post_def and text_line and text_line[0].isupper():
                        last_post = post_def[-1]
                        if last_post.rstrip().endswith((".", "!", "?")):
                            break
                    post_def.append(text_line)
                else:
                    break

            def_parts = pre_def + post_def

        definition = " ".join(def_parts).strip()
        if word and definition:
            vocab.append({"word": word, "definition": definition})

    return vocab


# ---------------------------------------------------------------------------
# NVR: Answer key only (questions are image-based)
# ---------------------------------------------------------------------------


def parse_nvr_answer_key(parent_guide_path: Path) -> dict[str, dict[int, str]]:
    """Parse NVR answer keys from Parent's Guide.

    NVR questions are visual, so we only extract answer keys for reference.
    Returns {"1": {1: "B", ...}, "2": {...}, "3": {...}}
    """
    pages = pdf_text_pages(parent_guide_path)
    all_answers = {}

    for page_text in pages:
        fam_match = re.search(
            r"Non-Verbal\s+Reasoning\s+Familiarisation\s+(\d+)",
            page_text,
            re.IGNORECASE,
        )
        if not fam_match:
            continue

        label = fam_match.group(1)
        answers = {}

        for m in re.finditer(r"(\d{1,2})\.\s+([A-E])\b", page_text):
            qnum = int(m.group(1))
            ans = m.group(2)
            if qnum not in answers:
                answers[qnum] = ans

        if answers:
            all_answers[label] = answers

    return all_answers


# ---------------------------------------------------------------------------
# Phase 1: Inspection
# ---------------------------------------------------------------------------


def inspect_pdfs():
    """Print structure information about each PDF."""
    print("=" * 70)
    print("PHASE 1: PDF Inspection")
    print("=" * 70)

    pdf_files = sorted(SAMPLES_DIR.rglob("*.pdf"))
    for path in pdf_files:
        rel = path.relative_to(SAMPLES_DIR)
        try:
            with pdfplumber.open(str(path)) as pdf:
                n_pages = len(pdf.pages)
                first_page_text = pdf.pages[0].extract_text() or "(no text)"
                first_line = first_page_text.split("\n")[0][:80]
            print(f"  {rel}: {n_pages} pages | {first_line}")
        except Exception as e:
            print(f"  {rel}: ERROR - {e}")


# ---------------------------------------------------------------------------
# Phase 2: Extraction
# ---------------------------------------------------------------------------


def extract_all() -> tuple[list[dict], list[dict]]:
    """Run all extractors. Returns (questions, vocabulary)."""
    all_questions = []
    stats = {}

    # --- English 1: GL Familiarisation ---
    print("\n--- English 1: GL Familiarisation ---")
    try:
        booklet = SAMPLES_DIR / "English" / "1" / "English_1_Test Booklet.pdf"
        parent_guide = SAMPLES_DIR / "English" / "1" / "English_Parent's Guide.pdf"

        if booklet.exists() and parent_guide.exists():
            answer_keys = parse_gl_english_answer_key(parent_guide)
            eng1_answers = answer_keys.get("1", {})
            print(f"  Answer key: {len(eng1_answers)} answers for Familiarisation 1")

            if eng1_answers:
                eng1_qs = extract_gl_english_1(booklet, eng1_answers)
                all_questions.extend(eng1_qs)
                stats["English 1 (GL)"] = len(eng1_qs)
                print(f"  Extracted: {len(eng1_qs)} questions")

            # Also try Familiarisation 2 if present in answer key
            eng2_answers = answer_keys.get("2", {})
            if eng2_answers:
                print(f"  Answer key: {len(eng2_answers)} answers for Familiarisation 2")
                print("  (No separate booklet 2 in samples, skipping extraction)")
                stats["English 2 answers (GL, no booklet)"] = 0
        else:
            print("  Booklet or parent guide not found, skipping")
    except Exception as e:
        print(f"  ERROR: {e}")

    # --- English 2: CGP Sample Paper ---
    print("\n--- English 2: CGP Sample Paper ---")
    try:
        booklet = (
            SAMPLES_DIR
            / "English"
            / "2"
            / "CGP-11-Plus-English-Sample-Paper Homework.pdf"
        )
        mark_scheme = (
            SAMPLES_DIR
            / "English"
            / "2"
            / "CGP-11-Plus-English-Sample-Paper-Mark-Scheme Homework.pdf"
        )

        if booklet.exists() and mark_scheme.exists():
            cgp_qs = extract_cgp_english(booklet, mark_scheme)
            all_questions.extend(cgp_qs)
            stats["English (CGP)"] = len(cgp_qs)
            print(f"  Extracted: {len(cgp_qs)} questions")
        else:
            print("  Booklet or mark scheme not found, skipping")
    except Exception as e:
        print(f"  ERROR: {e}")

    # --- VR 1: 11pluscentre Paper 2 ---
    print("\n--- VR 1: 11pluscentre Paper 2 ---")
    try:
        paper = SAMPLES_DIR / "VR" / "1" / "Paper 2.pdf"
        answers_pdf = SAMPLES_DIR / "VR" / "1" / "Paper 2 Answers.pdf"

        if paper.exists():
            # Note: Paper 2 Answers.pdf is image-only (scanned), not usable for text extraction
            if answers_pdf.exists():
                print("  Paper 2 Answers.pdf is image-only (scanned), skipping answer extraction")

            vr_paper2_qs = extract_vr_paper2(paper)
            all_questions.extend(vr_paper2_qs)
            stats["VR Paper 2 (11pluscentre, no answers)"] = len(vr_paper2_qs)
            print(f"  Extracted: {len(vr_paper2_qs)} questions (without verified answers)")
        else:
            print("  Paper not found, skipping")
    except Exception as e:
        print(f"  ERROR: {e}")

    # --- VR 2: GL Familiarisation 1-3 ---
    print("\n--- VR 2: GL Familiarisation 1-3 ---")
    try:
        parent_guide = SAMPLES_DIR / "VR" / "2" / "Verbal Reasoning_Parent's Guide.pdf"

        if parent_guide.exists():
            vr_answer_keys = parse_gl_vr_answer_key(parent_guide)
            print(f"  Answer keys found: booklets {list(vr_answer_keys.keys())}")

            for bnum_str, answers in sorted(vr_answer_keys.items()):
                bnum = int(bnum_str)
                booklet = (
                    SAMPLES_DIR
                    / "VR"
                    / "2"
                    / f"Verbal Reasoning_{bnum}_Test Booklet.pdf"
                )
                if not booklet.exists():
                    print(f"  Booklet {bnum}: not found, skipping")
                    continue

                print(f"  Booklet {bnum}: {len(answers)} answers")
                try:
                    vr_qs = extract_gl_vr_booklet(booklet, answers, bnum)
                    all_questions.extend(vr_qs)
                    stats[f"VR {bnum} (GL)"] = len(vr_qs)
                    print(f"    Extracted: {len(vr_qs)} questions")
                except Exception as e:
                    print(f"    ERROR extracting booklet {bnum}: {e}")
        else:
            print("  Parent guide not found, skipping")
    except Exception as e:
        print(f"  ERROR: {e}")

    # --- NVR: Answer keys only ---
    print("\n--- NVR: Answer keys only (image-based, skipping question extraction) ---")
    try:
        nvr_guide = (
            SAMPLES_DIR
            / "NVR"
            / "GL1-3"
            / "Non-Verbal Reasoning_Parent's Guide.pdf"
        )

        if nvr_guide.exists():
            nvr_answers = parse_nvr_answer_key(nvr_guide)
            for bnum, answers in sorted(nvr_answers.items()):
                print(f"  NVR Familiarisation {bnum}: {len(answers)} answers (keys only)")
            stats["NVR (answer keys only, no questions)"] = 0
        else:
            print("  Parent guide not found")
    except Exception as e:
        print(f"  ERROR: {e}")

    # --- Vocabulary ---
    print("\n--- Vocabulary: 550words.pdf ---")
    vocabulary = []
    try:
        vocab_path = SAMPLES_DIR / "English" / "words" / "550words.pdf"
        if vocab_path.exists():
            vocabulary = extract_vocabulary(vocab_path)
            stats["Vocabulary words"] = len(vocabulary)
            print(f"  Extracted: {len(vocabulary)} words with definitions")
        else:
            print("  550words.pdf not found, skipping")
    except Exception as e:
        print(f"  ERROR: {e}")

    return all_questions, vocabulary, stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print("=" * 70)
    print("Sample PDF Extraction Pipeline")
    print("=" * 70)
    print(f"Samples directory: {SAMPLES_DIR}")
    print(f"Output questions:  {OUTPUT_QUESTIONS}")
    print(f"Output vocabulary: {OUTPUT_VOCAB}")

    if not SAMPLES_DIR.exists():
        print(f"\nERROR: Samples directory not found: {SAMPLES_DIR}")
        sys.exit(1)

    # Phase 1: Inspect
    inspect_pdfs()

    # Phase 2: Extract
    print("\n" + "=" * 70)
    print("PHASE 2: Extraction")
    print("=" * 70)

    questions, vocabulary, stats = extract_all()

    # Phase 3: Save outputs
    print("\n" + "=" * 70)
    print("PHASE 3: Saving outputs")
    print("=" * 70)

    # Save questions
    OUTPUT_QUESTIONS.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_QUESTIONS, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)
    print(f"  Saved {len(questions)} questions to {OUTPUT_QUESTIONS}")

    # Save vocabulary
    if vocabulary:
        OUTPUT_VOCAB.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_VOCAB, "w", encoding="utf-8") as f:
            json.dump(vocabulary, f, indent=2, ensure_ascii=False)
        print(f"  Saved {len(vocabulary)} vocabulary words to {OUTPUT_VOCAB}")

    # Phase 4: Statistics
    print("\n" + "=" * 70)
    print("EXTRACTION SUMMARY")
    print("=" * 70)
    total_qs = 0
    for source, count in stats.items():
        print(f"  {source}: {count}")
        total_qs += count
    print(f"  {'=' * 40}")
    print(f"  TOTAL QUESTIONS: {len(questions)}")
    if vocabulary:
        print(f"  VOCABULARY WORDS: {len(vocabulary)}")

    # Show sample question
    if questions:
        print("\n--- Sample question ---")
        sample = questions[0]
        print(json.dumps(sample, indent=2, ensure_ascii=False)[:500])

    # Show sample vocabulary
    if vocabulary:
        print("\n--- Sample vocabulary ---")
        for v in vocabulary[:3]:
            print(f"  {v['word']}: {v['definition'][:80]}...")


if __name__ == "__main__":
    main()
