"""Generate verified 11+ GL Assessment questions using Gemini with two-pass verification.

Pipeline:
1. Generate questions at temperature 0.8 (creative diversity)
2. Verify each question with a second LLM call at temperature 0.0 (solve independently)
3. Only keep questions where both answers match
4. Dedup against existing question bank
5. Save incrementally per type

Usage:
    cd backend
    uv run python scripts/generate_verified_questions.py
    uv run python scripts/generate_verified_questions.py --subject maths
    uv run python scripts/generate_verified_questions.py --subject verbal_reasoning --type vr_anagrams
    uv run python scripts/generate_verified_questions.py --dry-run   # show what would be generated
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from google import genai

load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-2.0-flash"
VERIFY_MODEL = "gemini-2.0-flash"
DELAY_BETWEEN_BATCHES = 15  # seconds between API calls (avoid 429s)
BATCH_SIZE = 5  # generate N at a time (smaller = higher quality)

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "generated"
DUMP_PATH = Path(__file__).parent.parent / "data" / "questions" / "deployment_dump.json"

# What we need to generate (subject, type) -> target count
# Only types where we have a deficit or want type diversity
TARGETS = {
    # Maths - biggest gap (have 57, need 180)
    ("maths", "number_operations"): 19,
    ("maths", "fractions"): 25,
    ("maths", "geometry"): 11,
    ("maths", "measurement"): 7,
    ("maths", "word_problems"): 15,
    ("maths", "data_handling"): 15,
    ("maths", "algebra"): 20,
    ("maths", "ratio"): 19,
    ("maths", "decimals"): 6,
    ("maths", "percentages"): 6,
    # English - 42 deficit
    ("english", "comprehension"): 18,
    ("english", "vocabulary"): 10,
    ("english", "grammar"): 6,
    ("english", "spelling"): 4,
    ("english", "punctuation"): 4,
    # VR - fill missing types (12 types with 0 questions)
    ("verbal_reasoning", "vr_anagrams"): 6,
    ("verbal_reasoning", "vr_compound_words"): 6,
    ("verbal_reasoning", "vr_number_connections"): 6,
    ("verbal_reasoning", "vr_multiple_meaning"): 6,
    ("verbal_reasoning", "vr_letter_relationships"): 5,
    ("verbal_reasoning", "vr_number_codes"): 5,
    ("verbal_reasoning", "vr_word_shuffling"): 5,
    ("verbal_reasoning", "vr_explore_facts"): 5,
    ("verbal_reasoning", "vr_solve_riddle"): 5,
    ("verbal_reasoning", "vr_rhyming_synonyms"): 5,
    ("verbal_reasoning", "vr_shuffled_sentences"): 5,
    ("verbal_reasoning", "vr_letter_series"): 5,
    ("verbal_reasoning", "vr_odd_ones_out"): 5,
    # Top up thin types
    ("verbal_reasoning", "vr_number_series"): 5,
    ("verbal_reasoning", "vr_hidden_word"): 5,
}

# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------

from prompts.maths import MATHS_SYSTEM, get_maths_prompt
from prompts.verbal_reasoning import VR_SYSTEM, get_vr_prompt
from prompts.english import ENGLISH_SYSTEM, get_english_prompt


def get_system_prompt(subject: str) -> str:
    return {
        "maths": MATHS_SYSTEM,
        "verbal_reasoning": VR_SYSTEM,
        "english": ENGLISH_SYSTEM,
    }[subject]


def get_generation_prompt(subject: str, qtype: str, count: int) -> str:
    if subject == "maths":
        return get_maths_prompt(qtype, count)
    elif subject == "verbal_reasoning":
        return get_vr_prompt(qtype, count)
    elif subject == "english":
        return get_english_prompt(qtype, count)
    else:
        raise ValueError(f"No prompt for {subject}/{qtype}")


# ---------------------------------------------------------------------------
# Dedup
# ---------------------------------------------------------------------------


def normalize_text(text: str) -> str:
    t = text.lower().strip()
    t = re.sub(r"\s+", " ", t)
    return t


def text_trigrams(text: str) -> set[str]:
    t = normalize_text(text)
    return set(t[i : i + 3] for i in range(len(t) - 2))


def is_similar(a: str, b: str, threshold: float = 0.80) -> bool:
    """Check if two question texts are similar using trigram Jaccard."""
    ta, tb = text_trigrams(a), text_trigrams(b)
    if not ta or not tb:
        return normalize_text(a) == normalize_text(b)
    intersection = len(ta & tb)
    union = len(ta | tb)
    return (intersection / union) >= threshold if union > 0 else False


def load_existing_questions() -> list[dict]:
    """Load existing questions from deployment dump."""
    if not DUMP_PATH.exists():
        return []
    with open(DUMP_PATH) as f:
        return json.load(f)


def build_dedup_index(existing: list[dict]) -> dict[str, list[str]]:
    """Build per-type index of existing question texts for dedup."""
    index = defaultdict(list)
    for q in existing:
        text = q.get("content", {}).get("text", "")
        key = f"{q['subject']}/{q['question_type']}"
        index[key].append(text)
    return index


def _composite_key(question: dict) -> str:
    """Build a composite dedup key from text + answer + options."""
    text = normalize_text(question.get("content", {}).get("text", ""))
    answer = str(question.get("answer", {}).get("value", ""))
    options = "|".join(sorted(str(o) for o in question.get("content", {}).get("options", [])))
    return hashlib.sha256(f"{text}||{answer}||{options}".encode()).hexdigest()


# Types where questions share standardized instruction text but differ in actual content.
# These need composite dedup (text + answer + options) instead of text-only similarity.
_COMPOSITE_DEDUP_TYPES = {
    "spelling", "punctuation", "grammar",  # "Which sentence contains a spelling mistake?"
    "vr_insert_letter", "vr_hidden_word", "vr_missing_word", "vr_synonyms",
    "vr_alphabet_code", "vr_odd_ones_out", "vr_number_series", "vr_letter_series",
    "vr_number_connections", "vr_word_pairs", "vr_logic_problems",
    "vr_multiple_meaning", "vr_letter_relationships", "vr_number_codes",
    "vr_compound_words", "vr_word_shuffling", "vr_anagrams",
    "vr_explore_facts", "vr_solve_riddle", "vr_rhyming_synonyms",
    "vr_shuffled_sentences",
}


def is_duplicate(question: dict, dedup_index: dict[str, list[str]],
                 session_texts: list[str]) -> bool:
    """Check if a question duplicates existing or session questions."""
    qtype = question.get("question_type", "")

    # Types with shared preambles: dedup by composite key (text + answer + options)
    if qtype in _COMPOSITE_DEDUP_TYPES:
        comp = _composite_key(question)
        for st in session_texts:
            if st == comp:
                return True
        session_texts.append(comp)
        return False

    # For other types, use text similarity
    text = question.get("content", {}).get("text", "")
    key = f"{question['subject']}/{qtype}"
    for existing_text in dedup_index.get(key, []):
        if is_similar(text, existing_text):
            return True
    for st in session_texts:
        if is_similar(text, st):
            return True
    session_texts.append(text)
    return False


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def call_gemini(prompt: str, system: str, temperature: float = 0.8) -> str | None:
    """Call Gemini API with retries."""
    for attempt in range(4):
        try:
            response = gemini_client.models.generate_content(
                model=MODEL if temperature > 0 else VERIFY_MODEL,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=temperature,
                    system_instruction=system,
                    response_mime_type="application/json",
                ),
            )
            return response.text
        except Exception as e:
            wait = DELAY_BETWEEN_BATCHES * (attempt + 1)
            logger.warning(f"  Attempt {attempt + 1} failed: {e}")
            time.sleep(wait)
    return None


def parse_json_response(text: str) -> list[dict]:
    """Parse JSON from LLM response, handling common formatting issues."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    parsed = json.loads(text)
    if isinstance(parsed, dict):
        if "questions" in parsed:
            return parsed["questions"]
        for v in parsed.values():
            if isinstance(v, list):
                return v
        return []
    return parsed if isinstance(parsed, list) else []


def validate_question(q: dict) -> tuple[bool, str]:
    """Validate a generated question has all required fields and consistency."""
    if not isinstance(q, dict):
        return False, "Not a dict"

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
    if not options or len(options) < 4:
        return False, f"Only {len(options)} options (need at least 4)"

    # Check all options are distinct
    opt_lower = [str(o).lower().strip() for o in options]
    if len(set(opt_lower)) < len(opt_lower):
        return False, "Duplicate options"

    answer_val = q.get("answer", {}).get("value", "")
    if not answer_val:
        return False, "No answer value"

    # Check answer matches one of the options
    if str(answer_val) not in [str(o) for o in options]:
        # Try case-insensitive match
        ans_lower = str(answer_val).lower().strip()
        if ans_lower not in opt_lower:
            return False, f"Answer '{answer_val}' not in options"

    return True, "OK"


VERIFY_SYSTEM = """You are a question verification assistant. Your ONLY job is to solve
the given multiple-choice question and return the correct answer.
Return a JSON object: {"answer": "<exact text of the correct option>", "reasoning": "<brief explanation>"}
The answer field MUST be the EXACT text of one of the provided options. Do not paraphrase or explain the option."""


def verify_question(q: dict, system: str) -> bool:
    """Second-pass verification: ask LLM to solve the question independently."""
    content = q["content"]
    text = content["text"]
    options = content["options"]
    passage = content.get("passage", "")

    passage_text = f"\n\nPassage:\n{passage}" if passage else ""

    options_text = "\n".join(
        f"{chr(65+i)}) {options[i]}" for i in range(len(options))
    )

    verify_prompt = f"""Solve this multiple-choice question. Pick the correct answer from the options.
{passage_text}
Question: {text}

Options:
{options_text}

Return ONLY: {{"answer": "<exact text of the correct option>", "reasoning": "<1-2 sentence explanation>"}}"""

    response_text = call_gemini(verify_prompt, VERIFY_SYSTEM, temperature=0.0)
    if not response_text:
        return False

    try:
        parsed = json.loads(response_text.strip())
        # Handle case where model returns a list instead of dict
        if isinstance(parsed, list):
            if parsed and isinstance(parsed[0], dict):
                parsed = parsed[0]
            else:
                logger.warning("  Verification returned unexpected list format")
                return False
        if not isinstance(parsed, dict):
            logger.warning(f"  Verification returned unexpected type: {type(parsed)}")
            return False

        verified_answer = str(parsed.get("answer", "")).strip()
        expected_answer = str(q["answer"]["value"]).strip()

        # Normalize: strip "A) " or "C) " prefix from verifier answer
        if len(verified_answer) > 2 and verified_answer[1] == ")":
            verified_answer = verified_answer[2:].strip()

        # Check exact match or case-insensitive match
        if verified_answer == expected_answer:
            return True
        if verified_answer.lower() == expected_answer.lower():
            return True

        # Resolve verifier answer to option text if it's a letter
        letters = "ABCDE"
        resolved_answer = verified_answer
        if len(verified_answer) == 1 and verified_answer.upper() in letters:
            idx = letters.index(verified_answer.upper())
            if idx < len(options):
                resolved_answer = str(options[idx]).strip()

        # Check resolved answer against expected
        if resolved_answer == expected_answer:
            return True
        if resolved_answer.lower() == expected_answer.lower():
            return True

        # Final attempt: find which letter position each corresponds to
        expected_idx = None
        resolved_idx = None
        for i, opt in enumerate(options):
            opt_str = str(opt).strip()
            if opt_str == expected_answer or opt_str.lower() == expected_answer.lower():
                expected_idx = i
            if opt_str == resolved_answer or opt_str.lower() == resolved_answer.lower():
                resolved_idx = i
        if expected_idx is not None and expected_idx == resolved_idx:
            return True

        logger.warning(
            f"  Verification mismatch: expected '{expected_answer}', "
            f"got '{verified_answer}' (resolved: '{resolved_answer}')"
        )
        return False
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"  Verification parse error: {e}")
        return False


def generate_batch(subject: str, qtype: str, count: int) -> list[dict]:
    """Generate and verify a batch of questions."""
    system = get_system_prompt(subject)
    prompt = get_generation_prompt(subject, qtype, count)

    logger.info(f"Generating {count} {subject}/{qtype}...")
    text = call_gemini(prompt, system, temperature=0.8)
    if not text:
        logger.error(f"  Generation failed for {subject}/{qtype}")
        return []

    try:
        questions = parse_json_response(text)
    except json.JSONDecodeError as e:
        logger.error(f"  JSON parse error: {e}")
        return []

    # Validate structure
    valid = []
    for q in questions:
        ok, reason = validate_question(q)
        if ok:
            valid.append(q)
        else:
            logger.warning(f"  Invalid question: {reason}")

    logger.info(f"  Parsed {len(questions)}, {len(valid)} valid")

    # Two-pass verification
    verified = []
    for q in valid:
        if verify_question(q, system):
            verified.append(q)
        else:
            logger.warning(f"  Failed verification: {q['content']['text'][:60]}...")

    logger.info(f"  Verified: {len(verified)}/{len(valid)}")
    return verified


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Generate verified GL Assessment questions")
    parser.add_argument("--subject", help="Only generate for this subject")
    parser.add_argument("--type", help="Only generate for this question type")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be generated")
    parser.add_argument("--skip-verify", action="store_true", help="Skip two-pass verification")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing questions for dedup
    existing = load_existing_questions()
    dedup_index = build_dedup_index(existing)
    existing_counts = Counter(
        (q["subject"], q["question_type"]) for q in existing
    )

    # Load previously generated questions
    prev_generated = {}
    for gen_file in OUTPUT_DIR.glob("generated_*.json"):
        try:
            with open(gen_file) as f:
                gen_qs = json.load(f)
            if gen_qs:
                key = (gen_qs[0]["subject"], gen_qs[0]["question_type"])
                prev_generated[key] = prev_generated.get(key, []) + gen_qs
                # Add to dedup index
                for q in gen_qs:
                    text = q.get("content", {}).get("text", "")
                    idx_key = f"{q['subject']}/{q['question_type']}"
                    dedup_index[idx_key].append(text)
        except Exception:
            pass

    prev_counts = Counter({k: len(v) for k, v in prev_generated.items()})

    # Determine what to generate
    targets = {}
    for (subject, qtype), target in TARGETS.items():
        if args.subject and subject != args.subject:
            continue
        if args.type and qtype != args.type:
            continue

        have = existing_counts.get((subject, qtype), 0)
        have += prev_counts.get((subject, qtype), 0)
        need = max(0, target - prev_counts.get((subject, qtype), 0))

        if need > 0:
            targets[(subject, qtype)] = need

    if not targets:
        logger.info("Nothing to generate - all targets met")
        return

    # Show plan
    print("\n=== GENERATION PLAN ===")
    total_needed = 0
    for (subject, qtype), need in sorted(targets.items()):
        have_existing = existing_counts.get((subject, qtype), 0)
        have_prev = prev_counts.get((subject, qtype), 0)
        print(f"  {subject}/{qtype}: need {need} (existing: {have_existing}, prev generated: {have_prev})")
        total_needed += need
    print(f"  TOTAL: {total_needed} questions to generate")
    print()

    if args.dry_run:
        return

    # Generate
    all_new = []
    stats = {"generated": 0, "verified": 0, "deduped": 0, "saved": 0}

    for (subject, qtype), need in sorted(targets.items()):
        logger.info(f"\n{'='*40}")
        logger.info(f"Generating {need} {subject}/{qtype}")
        logger.info(f"{'='*40}")

        type_questions = []
        session_texts: list[str] = []  # for intra-batch dedup
        remaining = need
        attempts = 0
        max_attempts = (need // BATCH_SIZE + 2) * 3  # generous retry budget

        while remaining > 0 and attempts < max_attempts:
            attempts += 1
            batch_count = min(BATCH_SIZE, remaining)

            try:
                batch = generate_batch(subject, qtype, batch_count)
                stats["generated"] += len(batch)

                if args.skip_verify:
                    verified = batch
                else:
                    verified = batch  # already verified in generate_batch
                stats["verified"] += len(verified)

                # Dedup against existing + session
                new_questions = []
                for q in verified:
                    if is_duplicate(q, dedup_index, session_texts):
                        stats["deduped"] += 1
                        logger.info(f"  Dedup: {q['content']['text'][:50]}...")
                    else:
                        new_questions.append(q)
                        # Add to dedup index for future batches
                        text = q["content"]["text"]
                        idx_key = f"{q['subject']}/{q['question_type']}"
                        dedup_index[idx_key].append(text)

                type_questions.extend(new_questions)
                remaining -= len(new_questions)
                stats["saved"] += len(new_questions)

                logger.info(
                    f"  Progress: {len(type_questions)}/{need} for {subject}/{qtype}"
                )

                time.sleep(DELAY_BETWEEN_BATCHES)

            except Exception as e:
                logger.error(f"  Error: {e}")
                time.sleep(DELAY_BETWEEN_BATCHES * 2)

        # Save per type (merge with previously generated)
        prev = prev_generated.get((subject, qtype), [])
        all_for_type = prev + type_questions
        type_file = OUTPUT_DIR / f"generated_{subject}_{qtype}.json"
        with open(type_file, "w") as f:
            json.dump(all_for_type, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(all_for_type)} total {subject}/{qtype} to {type_file.name}")

        all_new.extend(type_questions)

    # Save combined file
    all_prev = [q for qs in prev_generated.values() for q in qs]
    combined = all_prev + all_new
    combined_file = OUTPUT_DIR / "all_generated.json"
    with open(combined_file, "w") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'='*60}")
    print("GENERATION SUMMARY")
    print(f"{'='*60}")
    print(f"  Generated: {stats['generated']}")
    print(f"  Verified:  {stats['verified']}")
    print(f"  Deduped:   {stats['deduped']}")
    print(f"  Saved:     {stats['saved']} new questions")
    print(f"  Combined:  {len(combined)} total generated questions")

    by_type = Counter(q["question_type"] for q in all_new)
    print(f"\nNew questions by type:")
    for t, c in by_type.most_common():
        print(f"  {t}: {c}")


if __name__ == "__main__":
    main()
