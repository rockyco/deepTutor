"""Build deployment_dump.json from all verified extraction sources.

Reads metadata.json files from CGP and GL Assessment extractions,
deduplicates by normalized question text, validates answers and images,
assigns question types, and outputs the final deployment dump.

Usage:
    uv run python backend/scripts/build_verified_dump.py
"""

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
IMAGES_DIR = PROJECT_ROOT / "backend" / "data" / "images"
DUMP_PATH = PROJECT_ROOT / "backend" / "data" / "questions" / "deployment_dump.json"

SUBJECTS = ["maths", "english", "verbal_reasoning", "non_verbal_reasoning"]

# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def normalize_text(text: str) -> str:
    """Normalize question text for deduplication."""
    t = text.lower().strip()
    # Remove whitespace variations
    t = re.sub(r"\s+", " ", t)
    # Remove common prefixes/markers
    t = re.sub(r"^passage:\s*", "", t)
    # Remove line references like "(lines 2-3)"
    t = re.sub(r"\(lines?\s*\d+[-\u2013]\d+\)", "", t)
    return t


def text_hash(text: str) -> str:
    """SHA256 hash of normalized text."""
    return hashlib.sha256(normalize_text(text).encode()).hexdigest()


def composite_hash(q: dict) -> str:
    """SHA256 hash of text + answer + sorted options.

    VR questions share long instruction preambles (e.g., "Choose two words,
    one from each set of brackets...") so text-only hashing falsely merges
    questions that have the same instructions but different content.
    """
    text = normalize_text(q.get("text", ""))
    answer = str(q.get("answer", "")).strip()
    options = "|".join(sorted(str(o) for o in q.get("options", [])))
    key = f"{text}||{answer}||{options}"
    return hashlib.sha256(key.encode()).hexdigest()


def fuzzy_similar(a: str, b: str, threshold: float = 0.85) -> bool:
    """Simple character-level similarity check."""
    na, nb = normalize_text(a), normalize_text(b)
    if na == nb:
        return True
    if not na or not nb:
        return False
    # Jaccard on character trigrams
    def trigrams(s):
        return set(s[i : i + 3] for i in range(len(s) - 2))
    ta, tb = trigrams(na), trigrams(nb)
    if not ta or not tb:
        return na == nb
    intersection = len(ta & tb)
    union = len(ta | tb)
    return (intersection / union) >= threshold if union > 0 else False


# ---------------------------------------------------------------------------
# Question type classification
# ---------------------------------------------------------------------------


def classify_maths_type(text: str) -> str:
    """Classify maths question into specific type."""
    t = text.lower()
    if any(w in t for w in ["shape", "angle", "triangle", "rectangle", "circle", "polygon",
                             "perimeter", "area", "volume", "parallel", "perpendicular",
                             "hexagon", "pentagon", "cube", "cuboid", "prism", "symmetry",
                             "reflect", "rotate", "coordinat"]):
        return "geometry"
    if any(w in t for w in ["fraction", "numerator", "denominator", "simplif",
                             "mixed number", "improper"]):
        return "fractions"
    if any(w in t for w in ["decimal", "0.", "tenths", "hundredths"]):
        return "decimals"
    if any(w in t for w in ["percent", "%"]):
        return "percentages"
    if any(w in t for w in ["graph", "chart", "pie chart", "bar chart", "tally",
                             "table", "pictogram", "frequency", "data", "survey"]):
        return "data_handling"
    if any(w in t for w in ["cm", "mm", "km", "metre", "meter", "litre", "liter",
                             "gram", "kilogram", "kg", "ml", "weight", "mass",
                             "length", "height", "capacity", "temperature", "celsius"]):
        return "measurement"
    if any(w in t for w in ["equation", "variable", "algebra", "solve for",
                             "unknown", "expression", "formula"]):
        return "algebra"
    if any(w in t for w in ["ratio", "proportion", "scale"]):
        return "ratio"
    if any(w in t for w in ["word problem", "how many", "how much", "altogether",
                             "difference", "total", "cost", "price", "bought", "sold",
                             "share", "divide equally", "each person"]):
        return "word_problems"
    return "number_operations"


def classify_english_type(text: str, has_passage: bool) -> str:
    """Classify English question into specific type."""
    t = text.lower()
    if has_passage or any(w in t for w in ["passage", "text", "author", "character",
                                            "paragraph", "line", "story", "poem"]):
        return "comprehension"
    if any(w in t for w in ["spell", "spelled", "spelling", "correctly spelt"]):
        return "spelling"
    if any(w in t for w in ["punctuat", "comma", "apostrophe", "full stop",
                             "speech mark", "colon", "semicolon", "capital letter"]):
        return "punctuation"
    if any(w in t for w in ["synonym", "antonym", "meaning", "definition",
                             "closest in meaning", "word means"]):
        return "vocabulary"
    if any(w in t for w in ["sentence", "verb", "noun", "adjective", "adverb",
                             "tense", "past", "present", "future", "plural",
                             "singular", "prefix", "suffix", "pronoun", "clause"]):
        return "grammar"
    return "comprehension"


def classify_vr_type(text: str) -> str:
    """Classify VR question into one of 21 GL types."""
    t = text.lower()

    if any(w in t for w in ["letter can be moved", "one letter", "find the letter that moves"]):
        return "vr_insert_letter"
    if any(w in t for w in ["odd one", "most unlike", "least like"]):
        return "vr_odd_ones_out"
    if any(w in t for w in ["code", "coded", "cipher", "alphabet code"]):
        return "vr_alphabet_code"
    if any(w in t for w in ["synonym", "closest in meaning", "similar meaning",
                             "same way as"]):
        return "vr_synonyms"
    if any(w in t for w in ["hidden word", "hidden in", "consecutive letters"]):
        return "vr_hidden_word"
    if any(w in t for w in ["missing word", "complete the sentence", "fits best",
                             "both sets of brackets"]):
        return "vr_missing_word"
    if any(w in t for w in ["number series", "number sequence", "next number",
                             "missing number"]) and any(c.isdigit() for c in t):
        return "vr_number_series"
    if any(w in t for w in ["letter series", "letter sequence", "next letter",
                             "missing letters"]):
        return "vr_letter_series"
    if any(w in t for w in ["number connection", "number relationship"]):
        return "vr_number_connections"
    if any(w in t for w in ["word pair", "pair of words", "go together",
                             "related", "opposite"]):
        return "vr_word_pairs"
    if any(w in t for w in ["multiple meaning", "two meanings"]):
        return "vr_multiple_meaning"
    if any(w in t for w in ["letter relationship"]):
        return "vr_letter_relationships"
    if any(w in t for w in ["number code"]):
        return "vr_number_codes"
    if any(w in t for w in ["compound word", "joined together"]):
        return "vr_compound_words"
    if any(w in t for w in ["rearrange", "shuffled", "anagram", "jumbled"]):
        return "vr_anagrams"
    if any(w in t for w in ["logic", "logical", "if", "therefore"]):
        return "vr_logic_problems"
    if any(w in t for w in ["three words", "first group", "second group",
                             "same way as the three"]):
        return "vr_word_pairs"
    return "vr_missing_word"  # Default VR type


def classify_nvr_type(text: str, source: str = "") -> str:
    """Classify NVR question type."""
    t = text.lower()
    if any(w in t for w in ["sequence", "series", "order", "next", "empty square"]):
        return "nvr_sequences"
    if any(w in t for w in ["odd one", "most unlike", "different"]):
        return "nvr_odd_one_out"
    if any(w in t for w in ["analog", "related", "goes with", "is to"]):
        return "nvr_analogies"
    if any(w in t for w in ["matrix", "grid", "missing piece", "pattern"]):
        return "nvr_matrices"
    if any(w in t for w in ["2d view", "top-down", "3d"]):
        return "nvr_spatial_3d"
    if any(w in t for w in ["rotat"]):
        return "nvr_rotation"
    if any(w in t for w in ["reflect", "mirror"]):
        return "nvr_reflection"
    if any(w in t for w in ["code"]):
        return "nvr_codes"
    return "nvr_visual"


# ---------------------------------------------------------------------------
# Build pipeline
# ---------------------------------------------------------------------------


def load_metadata(subject: str) -> list[dict]:
    """Load metadata.json for a subject."""
    path = IMAGES_DIR / f"granular_{subject}" / "metadata.json"
    if not path.exists():
        print(f"  WARNING: {path} not found")
        return []
    with open(path) as f:
        data = json.load(f)
    print(f"  Loaded {len(data)} questions from {path.name}")
    return data


def validate_question(q: dict, subject: str) -> tuple[bool, str]:
    """Validate a question entry. Returns (is_valid, reason)."""
    # Must have text
    text = q.get("text", "").strip()
    if not text:
        return False, "Empty question text"

    # Must have answer
    answer = q.get("answer", "")
    if not answer or answer == "Unknown":
        return False, f"Missing or unknown answer: '{answer}'"

    # Check options
    options = q.get("options", [])
    if not options:
        return False, "No options"
    if len(options) < 2:
        return False, f"Only {len(options)} option(s)"

    # Check image files exist (if referenced)
    img_dir = IMAGES_DIR / f"granular_{subject}"
    for img in q.get("question_images", []):
        if img and not (img_dir / img).exists():
            return False, f"Missing image: {img}"
    for img in q.get("images", []):
        if img and not (img_dir / img).exists():
            return False, f"Missing option image: {img}"

    return True, "OK"


def convert_to_dump_format(q: dict, subject: str) -> dict:
    """Convert metadata.json entry to deployment_dump.json format."""
    text = q.get("text", "")
    options = q.get("options", [])
    answer_raw = q.get("answer", "")
    explanation = q.get("explanation", "")
    source = q.get("source", "CGP Sample")
    passage = q.get("passage", None)

    # Classify question type
    if subject == "maths":
        q_type = classify_maths_type(text)
    elif subject == "english":
        q_type = classify_english_type(text, bool(passage))
    elif subject == "verbal_reasoning":
        q_type = classify_vr_type(text)
    else:
        q_type = classify_nvr_type(text, source)

    # Convert answer letter to value
    answer_value = answer_raw
    letters = "ABCDEFGH"  # Support up to 8 options
    if answer_raw in letters and options:
        idx = letters.index(answer_raw)
        if idx < len(options):
            answer_value = options[idx]
    # Handle "B Hippos" format (letter prefix + text)
    elif len(str(answer_raw)) > 1 and answer_raw[0] in letters and answer_raw[1] == " ":
        idx = letters.index(answer_raw[0])
        if idx < len(options):
            answer_value = options[idx]
    # Handle multi-answer format "B, D" or "A, F"
    if ", " in str(answer_raw) and all(
        c.strip() in letters for c in str(answer_raw).split(", ")
    ):
        indices = [letters.index(c.strip()) for c in str(answer_raw).split(", ")]
        answer_value = ", ".join(
            options[i] for i in indices if i < len(options)
        )

    # Fix spacing mismatches: if answer doesn't match any option, try normalized match
    if answer_value and options:
        opt_lower = [str(o).lower().strip() for o in options]
        ans_lower = str(answer_value).lower().strip()
        if ans_lower not in opt_lower:
            # Try without spaces
            ans_nospace = ans_lower.replace(" ", "")
            for i, o in enumerate(opt_lower):
                if o.replace(" ", "") == ans_nospace:
                    answer_value = options[i]
                    break

    # Build content
    content: dict = {"text": text, "options": options}

    # Add passage for English comprehension
    if passage:
        content["passage"] = passage

    # Add image URLs
    question_images = q.get("question_images", [])
    if question_images:
        content["image_url"] = f"/images/granular_{subject}/{question_images[0]}"
    elif q.get("question_image"):
        content["image_url"] = f"/images/granular_{subject}/{q['question_image']}"

    # Add option images for NVR
    option_images = q.get("images", [])
    if option_images:
        content["option_images"] = [
            f"/images/granular_{subject}/{img}" for img in option_images
        ]

    # Multi-select
    if ", " in str(answer_raw):
        content["multi_select"] = True

    return {
        "subject": subject,
        "question_type": q_type,
        "format": "multiple_choice",
        "difficulty": 3,
        "content": content,
        "answer": {"value": answer_value},
        "explanation": explanation,
        "hints": [],
        "tags": [],
        "source": source,
    }


def build_dump():
    """Main build pipeline."""
    print("=" * 60)
    print("Building Verified Deployment Dump")
    print("=" * 60)

    all_questions = []
    stats = defaultdict(lambda: defaultdict(int))

    for subject in SUBJECTS:
        print(f"\n--- {subject} ---")
        raw = load_metadata(subject)

        # Validate
        valid = []
        for q in raw:
            is_valid, reason = validate_question(q, subject)
            if is_valid:
                valid.append(q)
            else:
                stats[subject]["invalid"] += 1

        print(f"  Valid: {len(valid)}, Invalid: {stats[subject]['invalid']}")

        # Deduplicate by hash
        # VR: use composite key (text + answer + options) because VR questions
        #     share long instruction preambles but have different actual content
        # NVR CGP: use text + answer (same questions appear with different images)
        # NVR GL: use question image (text is generic but images are unique)
        # Others: use normalized question text
        seen_hashes = set()
        deduped = []
        for q in valid:
            source = q.get("source", "CGP Sample")
            if subject == "verbal_reasoning":
                h = composite_hash(q)
            elif subject == "non_verbal_reasoning" and "GL Assessment" in source:
                # GL NVR: each booklet question is unique by position
                imgs = tuple(q.get("question_images", []))
                answer = q.get("answer", "")
                key = f"{imgs}|{answer}|{source}"
                h = hashlib.sha256(key.encode()).hexdigest()
            elif subject == "non_verbal_reasoning":
                # CGP NVR: dedup by text + answer (same question, different image files)
                text = normalize_text(q.get("text", ""))
                answer = q.get("answer", "")
                key = f"{text}|{answer}"
                h = hashlib.sha256(key.encode()).hexdigest()
            else:
                h = text_hash(q.get("text", ""))
            if h not in seen_hashes:
                seen_hashes.add(h)
                deduped.append(q)
            else:
                stats[subject]["deduped_hash"] += 1

        print(f"  After hash dedup: {len(deduped)} (removed {stats[subject]['deduped_hash']})")

        # Fuzzy dedup on remaining
        # Skip for NVR (text is generic) and VR (already composite-hashed;
        # fuzzy on text alone produces false positives due to shared preambles)
        final = []
        if subject in ("non_verbal_reasoning", "verbal_reasoning"):
            final = deduped
        else:
            for q in deduped:
                is_dup = False
                for existing in final:
                    if fuzzy_similar(q.get("text", ""), existing.get("text", "")):
                        is_dup = True
                        stats[subject]["deduped_fuzzy"] += 1
                        break
                if not is_dup:
                    final.append(q)

        fuzzy_cnt = stats[subject].get('deduped_fuzzy', 0)
        print(f"  After fuzzy dedup: {len(final)} (removed {fuzzy_cnt})")

        # Convert to dump format
        converted = [convert_to_dump_format(q, subject) for q in final]
        all_questions.extend(converted)
        stats[subject]["final"] = len(converted)

    # Save
    print(f"\n{'=' * 60}")
    print(f"Writing {len(all_questions)} questions to {DUMP_PATH}")

    with open(DUMP_PATH, "w") as f:
        json.dump(all_questions, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'=' * 60}")
    print("Summary")
    print(f"{'=' * 60}")
    total = 0
    for subject in SUBJECTS:
        count = stats[subject]["final"]
        total += count
        print(f"  {subject}: {count} questions")
        if stats[subject]["invalid"]:
            print(f"    - {stats[subject]['invalid']} invalid (removed)")
        if stats[subject]["deduped_hash"]:
            print(f"    - {stats[subject]['deduped_hash']} exact duplicates (removed)")
        if stats[subject]["deduped_fuzzy"]:
            print(f"    - {stats[subject]['deduped_fuzzy']} fuzzy duplicates (removed)")
    print(f"  TOTAL: {total} verified questions")

    # Source breakdown
    source_counts = defaultdict(int)
    type_counts = defaultdict(lambda: defaultdict(int))
    for q in all_questions:
        source_counts[q.get("source", "Unknown")] += 1
        type_counts[q["subject"]][q["question_type"]] += 1

    print("\nBy source:")
    for src, cnt in sorted(source_counts.items()):
        print(f"  {src}: {cnt}")

    print("\nBy type:")
    for subj in SUBJECTS:
        if subj in type_counts:
            print(f"  {subj}:")
            for qtype, cnt in sorted(type_counts[subj].items()):
                print(f"    {qtype}: {cnt}")

    return all_questions


if __name__ == "__main__":
    build_dump()
