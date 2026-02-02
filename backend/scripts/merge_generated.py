"""Merge generated questions into the deployment dump.

Reads generated questions from data/generated/, validates them,
normalizes type names, and appends to deployment_dump.json.

Usage:
    cd backend
    uv run python scripts/merge_generated.py
    uv run python scripts/merge_generated.py --dry-run
"""

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

GENERATED_DIR = Path(__file__).parent.parent / "data" / "generated"
DUMP_PATH = Path(__file__).parent.parent / "data" / "questions" / "deployment_dump.json"

# Valid types from the QuestionType enum in app/models/question.py
VALID_TYPES = {
    # English
    "comprehension", "grammar", "spelling", "vocabulary",
    "sentence_completion", "punctuation",
    # Maths
    "number_operations", "fractions", "decimals", "percentages",
    "geometry", "measurement", "data_handling", "word_problems",
    "algebra", "ratio",
    # VR
    "vr_insert_letter", "vr_odd_ones_out", "vr_alphabet_code",
    "vr_synonyms", "vr_hidden_word", "vr_missing_word",
    "vr_number_series", "vr_letter_series", "vr_number_connections",
    "vr_word_pairs", "vr_multiple_meaning", "vr_letter_relationships",
    "vr_number_codes", "vr_compound_words", "vr_word_shuffling",
    "vr_anagrams", "vr_logic_problems", "vr_explore_facts",
    "vr_solve_riddle", "vr_rhyming_synonyms", "vr_shuffled_sentences",
    # NVR
    "nvr_sequences", "nvr_odd_one_out", "nvr_analogies",
    "nvr_matrices", "nvr_rotation", "nvr_reflection",
    "nvr_spatial_3d", "nvr_codes", "nvr_visual",
}

# Type name normalization map (handle common variations)
TYPE_NORMALIZE = {
    "odd_ones_out": "vr_odd_ones_out",
    "hidden_word": "vr_hidden_word",
    "missing_word": "vr_missing_word",
    "insert_letter": "vr_insert_letter",
    "alphabet_code": "vr_alphabet_code",
    "number_series": "vr_number_series",
    "letter_series": "vr_letter_series",
    "word_pairs": "vr_word_pairs",
    "logic_problems": "vr_logic_problems",
    "synonyms": "vr_synonyms",
}


def normalize_type(q: dict) -> str:
    """Normalize question type to match the QuestionType enum."""
    qtype = q.get("question_type", "")
    subject = q.get("subject", "")

    # Apply normalization for VR types without prefix
    if subject == "verbal_reasoning" and qtype in TYPE_NORMALIZE:
        return TYPE_NORMALIZE[qtype]

    return qtype


def validate_generated(q: dict) -> tuple[bool, str]:
    """Validate a generated question for merging."""
    # Required fields
    for field in ("subject", "question_type", "content", "answer"):
        if field not in q:
            return False, f"Missing field: {field}"

    content = q.get("content", {})
    if not isinstance(content, dict):
        return False, "Content is not a dict"

    text = content.get("text", "")
    if not text or len(text) < 10:
        return False, "Question text too short"

    options = content.get("options", [])
    if len(options) < 4:
        return False, f"Only {len(options)} options"

    answer_val = str(q.get("answer", {}).get("value", ""))
    if not answer_val:
        return False, "No answer value"

    # Check answer is in options
    if answer_val not in [str(o) for o in options]:
        # Case-insensitive fallback
        if answer_val.lower() not in [str(o).lower() for o in options]:
            return False, f"Answer '{answer_val}' not in options"

    # Check type is valid
    qtype = normalize_type(q)
    if qtype not in VALID_TYPES:
        return False, f"Invalid type: {qtype}"

    return True, "OK"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Load existing dump
    existing = []
    if DUMP_PATH.exists():
        with open(DUMP_PATH) as f:
            existing = json.load(f)
    print(f"Existing dump: {len(existing)} questions")

    # Also normalize types in existing dump
    type_fixes = 0
    for q in existing:
        old_type = q["question_type"]
        new_type = normalize_type(q)
        if new_type != old_type:
            q["question_type"] = new_type
            type_fixes += 1
    if type_fixes:
        print(f"Normalized {type_fixes} type names in existing dump")

    # Load generated questions
    generated = []
    for gen_file in sorted(GENERATED_DIR.glob("generated_*.json")):
        try:
            with open(gen_file) as f:
                qs = json.load(f)
            print(f"  {gen_file.name}: {len(qs)} questions")
            generated.extend(qs)
        except Exception as e:
            print(f"  {gen_file.name}: ERROR - {e}")

    if not generated:
        print("No generated questions found")
        return

    print(f"\nTotal generated: {len(generated)}")

    # Validate
    valid = []
    invalid_reasons = Counter()
    for q in generated:
        ok, reason = validate_generated(q)
        if ok:
            # Normalize type
            q["question_type"] = normalize_type(q)
            valid.append(q)
        else:
            invalid_reasons[reason] += 1

    print(f"Valid: {len(valid)}, Invalid: {len(generated) - len(valid)}")
    if invalid_reasons:
        for reason, count in invalid_reasons.most_common():
            print(f"  - {reason}: {count}")

    # Check answer distribution (flag clustering)
    by_type = defaultdict(list)
    for q in valid:
        by_type[q["question_type"]].append(q)

    print("\nAnswer position distribution:")
    for qtype, qs in sorted(by_type.items()):
        positions = Counter()
        for q in qs:
            answer = str(q["answer"]["value"])
            options = q["content"]["options"]
            for i, opt in enumerate(options):
                if str(opt) == answer:
                    positions[chr(65 + i)] += 1
                    break
        dist = " ".join(f"{k}:{v}" for k, v in sorted(positions.items()))
        print(f"  {qtype} ({len(qs)}): {dist}")

    if args.dry_run:
        print("\n[DRY RUN] Would merge {len(valid)} questions")
        return

    # Merge
    merged = existing + valid
    print(f"\nMerged: {len(merged)} total ({len(existing)} existing + {len(valid)} new)")

    with open(DUMP_PATH, "w") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"Written to {DUMP_PATH}")

    # Final summary
    by_subject = Counter(q["subject"] for q in merged)
    print("\nFinal counts by subject:")
    for s, c in by_subject.most_common():
        print(f"  {s}: {c}")

    print("\nFinal counts by type:")
    by_type_final = Counter(f"{q['subject']}/{q['question_type']}" for q in merged)
    for t, c in sorted(by_type_final.items()):
        print(f"  {t}: {c}")


if __name__ == "__main__":
    main()
