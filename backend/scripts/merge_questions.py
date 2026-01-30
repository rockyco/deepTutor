"""Merge existing and generated questions into deployment_dump.json.

Combines:
1. Existing questions from deployment_dump.json
2. Generated questions from data/generated/
3. Reclassifies English questions as needed
4. Deduplicates by question text similarity
5. Validates schema compliance
"""

import json
import logging
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
QUESTIONS_DIR = DATA_DIR / "questions"
GENERATED_DIR = DATA_DIR / "generated"
OUTPUT_FILE = QUESTIONS_DIR / "deployment_dump.json"

# Valid subjects and types
VALID_SUBJECTS = {"english", "maths", "verbal_reasoning", "non_verbal_reasoning"}
VALID_TYPES = {
    "english": {"comprehension", "grammar", "spelling", "vocabulary", "sentence_completion", "punctuation"},
    "maths": {"number_operations", "fractions", "decimals", "percentages", "geometry", "measurement", "data_handling", "word_problems", "algebra", "ratio"},
    "verbal_reasoning": {
        "vr_insert_letter", "vr_odd_ones_out", "vr_alphabet_code", "vr_synonyms",
        "vr_hidden_word", "vr_missing_word", "vr_number_series", "vr_letter_series",
        "vr_number_connections", "vr_word_pairs", "vr_multiple_meaning",
        "vr_letter_relationships", "vr_number_codes", "vr_compound_words",
        "vr_word_shuffling", "vr_anagrams", "vr_logic_problems", "vr_explore_facts",
        "vr_solve_riddle", "vr_rhyming_synonyms", "vr_shuffled_sentences",
    },
    "non_verbal_reasoning": {
        "nvr_sequences", "nvr_odd_one_out", "nvr_analogies", "nvr_matrices",
        "nvr_rotation", "nvr_reflection", "nvr_spatial_3d", "nvr_codes", "nvr_visual",
    },
}


def reclassify_english(question: dict) -> dict:
    """Reclassify English 'grammar' questions into comprehension or vocabulary."""
    if question["subject"] != "english":
        return question
    if question["question_type"] not in ("grammar",):
        return question

    text = question["content"].get("text", "").lower()
    has_passage = bool(question["content"].get("passage"))

    if has_passage or "passage" in text or "read" in text:
        question["question_type"] = "comprehension"
    else:
        # Default grammar questions to vocabulary for the mock exam
        question["question_type"] = "vocabulary"

    return question


def validate_question(q: dict) -> bool:
    """Validate a question has all required fields and valid values."""
    # Required fields
    if not all(k in q for k in ("subject", "question_type", "content", "answer")):
        return False

    # Valid subject
    if q["subject"] not in VALID_SUBJECTS:
        return False

    # Valid type for subject
    subject_types = VALID_TYPES.get(q["subject"], set())
    if q["question_type"] not in subject_types:
        return False

    # Content must have text and options
    content = q.get("content", {})
    if not isinstance(content, dict):
        return False
    if not content.get("text"):
        return False
    if not content.get("options") or len(content["options"]) < 2:
        return False

    # Answer must have value
    answer = q.get("answer", {})
    if not isinstance(answer, dict):
        return False
    if not answer.get("value"):
        return False

    return True


def deduplicate(questions: list[dict]) -> list[dict]:
    """Remove duplicate questions by text similarity."""
    seen_texts = set()
    unique = []

    for q in questions:
        text = q["content"].get("text", "").strip().lower()
        # Normalize whitespace
        text = " ".join(text.split())

        if text in seen_texts:
            continue
        seen_texts.add(text)
        unique.append(q)

    return unique


def main():
    # 1. Load existing questions
    existing = []
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            existing = json.load(f)
    logger.info(f"Existing questions: {len(existing)}")

    # 2. Reclassify English questions
    reclassified = [reclassify_english(q) for q in existing]

    # 3. Load generated questions
    generated = []
    if GENERATED_DIR.exists():
        for f in sorted(GENERATED_DIR.glob("*.json")):
            if f.name == "all_generated.json":
                continue
            try:
                with open(f) as fh:
                    qs = json.load(fh)
                if isinstance(qs, list):
                    generated.extend(qs)
                    logger.info(f"  Loaded {len(qs)} from {f.name}")
            except Exception as e:
                logger.warning(f"  Error loading {f.name}: {e}")

    logger.info(f"Generated questions: {len(generated)}")

    # 4. Merge all
    all_questions = reclassified + generated

    # 5. Ensure required fields with defaults
    for q in all_questions:
        q.setdefault("format", "multiple_choice")
        q.setdefault("difficulty", 3)
        q.setdefault("explanation", "")
        q.setdefault("hints", [])
        q.setdefault("tags", [])
        q.setdefault("source", "Unknown")

    # 6. Validate
    valid = [q for q in all_questions if validate_question(q)]
    invalid_count = len(all_questions) - len(valid)
    if invalid_count > 0:
        logger.warning(f"Removed {invalid_count} invalid questions")

    # 7. Deduplicate
    unique = deduplicate(valid)
    dup_count = len(valid) - len(unique)
    if dup_count > 0:
        logger.info(f"Removed {dup_count} duplicates")

    # 8. Write output
    with open(OUTPUT_FILE, "w") as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    # 9. Summary
    by_subject = Counter(q["subject"] for q in unique)
    by_type = Counter(q["question_type"] for q in unique)

    print(f"\n{'='*50}")
    print(f"MERGE SUMMARY")
    print(f"{'='*50}")
    print(f"Total questions: {len(unique)}")
    print(f"\nBy subject:")
    for s, c in sorted(by_subject.items()):
        print(f"  {s}: {c}")
    print(f"\nBy type:")
    for t, c in by_type.most_common():
        print(f"  {t}: {c}")

    # Check against targets
    print(f"\n{'='*50}")
    print(f"EXAM COVERAGE CHECK (need 180 per exam, 540 for 3 exams)")
    print(f"{'='*50}")
    targets = {
        "english": 120,
        "maths": 180,
        "non_verbal_reasoning": 120,
        "verbal_reasoning": 120,
    }
    for subj, target in targets.items():
        have = by_subject.get(subj, 0)
        status = "OK" if have >= target else f"NEED {target - have} MORE"
        print(f"  {subj}: {have}/{target} [{status}]")

    print(f"\nOutput: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
