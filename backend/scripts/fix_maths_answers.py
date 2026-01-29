"""Fix maths question answers in deployment_dump.json.

Problems found:
1. Letter answers ("A", "B", etc.) instead of option text
2. "Unknown" answers with wrong explanation (all got Q11/knitting explanation)
3. Duplicate questions (Q11-Q20 duplicate Q1-Q10 with shuffled options)

Fix strategy:
- Convert letter answers to actual option text
- Compute correct answers for Unknown questions
- Write correct explanations for previously-Unknown questions
- Remove duplicate questions
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "questions"
DUMP_FILE = DATA_DIR / "deployment_dump.json"

# Letter to index: A=0, B=1, C=2, D=3, E=4
LETTER_TO_IDX = {chr(65 + i): i for i in range(6)}

# Correct answers and explanations for questions that had "Unknown" + wrong explanation.
# Keyed by question text prefix (first 50 chars after whitespace normalization).
MANUAL_FIXES = {
    "41": {
        "answer_text": "8",
        "explanation": "3h = 41 - 17 = 24, so h = 24 \u00f7 3 = 8.",
    },
    "A chip shop records": {
        "answer_text": "It doesn\u2019t include other options, such as ketchup.",
        "explanation": "The chart only shows data about salt and vinegar, but people might have other toppings on their chips. A chart that doesn\u2019t show all the options can be misleading because it doesn\u2019t give the full picture.",
    },
    "Marko is at a toy shop": {
        "answer_text": "2\u00a0\u00d7\u00a0\u00a35.00 +\u00a03\u00a0\u00d7\u00a0\u00a34.00 +\u00a0\u00a33.50\u00a0\u2212\u00a06p",
        "explanation": "The prices are: Chickens \u00a33.99, Dinosaurs \u00a34.99, Tigers \u00a33.49. Each price is 1p less than a round number. So the cost is 2 \u00d7 (\u00a35.00 \u2212 1p) + 3 \u00d7 (\u00a34.00 \u2212 1p) + (\u00a33.50 \u2212 1p) = 2 \u00d7 \u00a35.00 + 3 \u00d7 \u00a34.00 + \u00a33.50 \u2212 6p.",
    },
    "Milly collected some data": {
        "answer_text": "7",
        "explanation": "Total dogs = 34, Total males = 15, so Total females = 34 \u2212 15 = 19. Female adults = 12, so Female puppies = 19 \u2212 12 = 7.",
    },
    "What is the remainder when 2576": {
        "answer_text": "2",
        "explanation": "2576 \u00f7 9 = 286 remainder 2. Check: 286 \u00d7 9 = 2574, and 2576 \u2212 2574 = 2.",
    },
}


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def find_manual_fix(question_text: str) -> dict | None:
    norm = normalize_text(question_text)
    for prefix, fix in MANUAL_FIXES.items():
        if norm.startswith(prefix):
            return fix
    return None


def fix_answer(question: dict) -> dict:
    """Fix a single maths question's answer."""
    content = question.get("content", {})
    answer = question.get("answer", {})
    options = content.get("options", [])
    answer_val = answer.get("value", "")
    question_text = content.get("text", "")

    if not options:
        return question

    # Case 1: Letter answer - convert to option text
    if answer_val in LETTER_TO_IDX:
        idx = LETTER_TO_IDX[answer_val]
        if idx < len(options):
            answer["value"] = options[idx]
            question["answer"] = answer
            return question

    # Case 2: Unknown answer - look up manual fix or find matching option
    if answer_val in ("Unknown", "", None):
        fix = find_manual_fix(question_text)
        if fix:
            answer["value"] = fix["answer_text"]
            question["answer"] = answer
            question["explanation"] = fix["explanation"]
            return question

        # For duplicates of Q1-Q10 that just have shuffled options,
        # try to find the correct answer from the known Q1-Q10 answers.
        # These are handled by the deduplication step.

    return question


def deduplicate_questions(questions: list[dict]) -> list[dict]:
    """Remove duplicate maths questions (same text, different option order)."""
    seen_texts = set()
    unique = []
    for q in questions:
        if q.get("subject") != "maths":
            unique.append(q)
            continue

        text = normalize_text(q.get("content", {}).get("text", ""))
        if text in seen_texts:
            continue
        seen_texts.add(text)
        unique.append(q)

    return unique


def main():
    with open(DUMP_FILE) as f:
        data = json.load(f)

    questions = data if isinstance(data, list) else data.get("questions", [])

    maths_before = sum(1 for q in questions if q.get("subject") == "maths")
    print(f"Before fix: {len(questions)} total, {maths_before} maths")

    # Step 1: Fix answers
    for q in questions:
        if q.get("subject") == "maths":
            fix_answer(q)

    # Step 2: Deduplicate
    questions = deduplicate_questions(questions)

    maths_after = sum(1 for q in questions if q.get("subject") == "maths")
    print(f"After fix:  {len(questions)} total, {maths_after} maths")
    print(f"  Removed {maths_before - maths_after} duplicate maths questions")

    # Verify: check all maths answers are now option text, not letters or Unknown
    issues = 0
    for q in questions:
        if q.get("subject") != "maths":
            continue
        ans_val = q.get("answer", {}).get("value", "")
        opts = q.get("content", {}).get("options", [])
        if ans_val in ("Unknown", "", None):
            text = normalize_text(q.get("content", {}).get("text", ""))[:80]
            print(f"  STILL UNKNOWN: {text}")
            issues += 1
        elif ans_val in LETTER_TO_IDX:
            print(f"  STILL LETTER: {ans_val}")
            issues += 1
        elif opts and ans_val not in opts:
            text = normalize_text(q.get("content", {}).get("text", ""))[:80]
            print(f"  NOT IN OPTIONS: answer='{ans_val}' | {text}")
            issues += 1

    if issues == 0:
        print("  All maths answers verified OK!")

    # Save
    if isinstance(data, dict):
        data["questions"] = questions
        output = data
    else:
        output = questions

    with open(DUMP_FILE, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nSaved to {DUMP_FILE}")


if __name__ == "__main__":
    main()
