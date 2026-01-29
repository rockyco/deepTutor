"""Fix English and Verbal Reasoning question answers in deployment_dump.json.

Same corruption pattern as maths:
1. Letter answers ("A", "B", etc.) instead of option text
2. "Unknown" answers with wrong explanation (English got Q11/alliteration explanation,
   VR got Q11/below explanation)
3. Duplicate questions (Q11-Q20 duplicate Q1-Q10 with shuffled options)

Additionally, VR has multi-select answers ("B, D") that need conversion to option texts.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "questions"
DUMP_FILE = DATA_DIR / "deployment_dump.json"

LETTER_TO_IDX = {chr(65 + i): i for i in range(6)}  # A=0..F=5


def normalize_text(text: str) -> str:
    return " ".join(text.split())


# ── Manual fixes keyed by a SUBSTRING found anywhere in the question text ────
# Each entry: {"match": substring, "answer_text": str, "explanation": str}

ENGLISH_FIXES = [
    {
        # Q12: "womens'" should be "women's"
        "match": "womens",
        "answer_text": "that our womens\u2019 football",
        "explanation": (
            "Answer:\n\n\u2018womens\u2019\u2019 is wrong. \u2018Women\u2019 is already plural, "
            "so the possessive is \u2018women\u2019s\u2019, not \u2018womens\u2019\u2019."
        ),
    },
    {
        # Q13: "taste like heaven" = simile
        "match": "squashed sandwiches",
        "answer_text": "simile",
        "explanation": (
            "Answer:\n\n\u2018taste like heaven\u2019 is a simile. A simile compares two things "
            "using \u2018like\u2019 or \u2018as\u2019. Here, the taste of the sandwiches is "
            "compared to heaven using \u2018like\u2019."
        ),
    },
    {
        # Q14: Duplicate of Q8 (metaphor - panther), handled by dedup
        # But in case dedup keeps the wrong one, fix it too
        "match": "panther stalking",
        "answer_text": "Serena took games of hide-and-seek very seriously: she was a panther stalking in the jungle.",
        "explanation": (
            "Answer:\n\nA metaphor describes something as being something else. "
            "Serena is not literally a panther stalking in the jungle \u2014 she is described "
            "like this to show how she is searching for her friends, "
            "so this sentence contains a metaphor."
        ),
    },
    {
        # Q15: Missing comma after "Margaret"
        "match": "Geoffrey and Margaret",
        "answer_text": "Geoffrey and Margaret the",
        "explanation": (
            "Answer:\n\n\u2018the quick-witted parrots\u2019 is extra information about Geoffrey "
            "and Margaret, so it should be separated by commas. There should be a comma after "
            "\u2018Margaret\u2019: \u2018Geoffrey and Margaret, the quick-witted parrots, amused "
            "everyone...\u2019"
        ),
    },
    {
        # Q16: Duplicate of Q3 (William's brother - no mistake), handled by dedup
        "match": "William",
        "answer_text": "No mistake",
        "explanation": "Answer:\n\nThere are no mistakes in this sentence.",
    },
    {
        # Q17: "must" is a modal verb
        "match": "must",
        "answer_text": "modal verb",
        "explanation": (
            "Answer:\n\n\u2018must\u2019 is a modal verb. Modal verbs express necessity, "
            "possibility, or permission. Here, \u2018must\u2019 expresses that arriving "
            "promptly is required."
        ),
    },
    {
        # Q18: "soon" is an adverb
        "match": "adverb",
        "answer_text": "soon",
        "explanation": (
            "Answer:\n\n\u2018soon\u2019 is an adverb. It tells you when the action of going "
            "for a stroll will happen. \u2018Today\u2019 functions as a noun (subject) in this "
            "sentence, \u2018gentle\u2019 and \u2018lovely\u2019 are adjectives, and \u2018will\u2019 "
            "is a modal verb."
        ),
    },
    {
        # Q19: Duplicate of Q10 (freezing = adjective), handled by dedup
        "match": "freezing",
        "answer_text": "adjective",
        "explanation": (
            "Answer:\n\n\u2018freezing\u2019 is an adjective in this sentence. "
            "It describes the noun \u2018lake\u2019."
        ),
    },
    {
        # Q20: Missing commas in list
        "match": "Isla",
        "answer_text": "mountains kayaking on a lake",
        "explanation": (
            "Answer:\n\nThe list of activities needs commas to separate items: "
            "\u2018hiking in the mountains, kayaking on a lake, and swimming\u2019. "
            "The missing commas are in \u2018mountains kayaking on a lake\u2019."
        ),
    },
]

VR_FIXES = [
    {
        # Q12: Number codes - LIFT = 5236
        "match": "FLIP",
        "answer_text": "5236",
        "explanation": (
            "Answer:\n\nWork out the letter-number mapping: FLIP=3521 gives F=3, L=5, I=2, P=1. "
            "LIPS=5214 gives L=5, I=2, P=1, S=4 (consistent). So LIFT = L,I,F,T = 5,2,3,T. "
            "The remaining code 5236 fits with T=6. LIFT = 5236."
        ),
    },
    {
        # Q13: 44 - 27 = 17, 68/17 = 4
        "match": "68",
        "answer_text": "4",
        "explanation": (
            "Answer:\n\n44 \u2212 27 = 17. So 68 \u00f7 (?) = 17, "
            "which means (?) = 68 \u00f7 17 = 4."
        ),
    },
    {
        # Q14: Letter sequence DH,HI,LJ,PK,TL -> XM
        "match": "DH",
        "answer_text": "XM",
        "explanation": (
            "Answer:\n\nThe first letter increases by 4 each time: D, H, L, P, T, X. "
            "The second letter increases by 1 each time: H, I, J, K, L, M. "
            "So the next pair is XM."
        ),
    },
    {
        # Q15: strum->must (positions 5,4,1,2), ideal->laid
        "match": "strum",
        "answer_text": "laid",
        "explanation": (
            "Answer:\n\nThe pattern takes letters at positions 5, 4, 1, 2 of the first word. "
            "strum \u2192 m(5), u(4), s(1), t(2) = must. "
            "asset \u2192 t(5), e(4), a(1), s(2) = teas. "
            "ideal \u2192 l(5), a(4), i(1), d(2) = laid."
        ),
    },
    {
        # Q16: committee/panel/council are linked; society/community are not
        "match": "Three of the words below are linked",
        "answer_text": "society, community",
        "explanation": (
            "Answer:\n\n\u2018committee\u2019, \u2018panel\u2019 and \u2018council\u2019 are all "
            "organised groups of people with a specific decision-making purpose. "
            "\u2018society\u2019 and \u2018community\u2019 are broader social groups, so they "
            "are the two unrelated words."
        ),
    },
    {
        # Q17: right*(left-1) pattern -> 6*7 = 42
        "match": "5 (16) 4",
        "answer_text": "42",
        "explanation": (
            "Answer:\n\nThe pattern is: middle = right number \u00d7 (left number \u2212 1). "
            "5 (16) 4: 4 \u00d7 (5\u22121) = 4 \u00d7 4 = 16. "
            "3 (14) 7: 7 \u00d7 (3\u22121) = 7 \u00d7 2 = 14. "
            "8 (?) 6: 6 \u00d7 (8\u22121) = 6 \u00d7 7 = 42."
        ),
    },
    {
        # Q18: yell(dye)head -> last/1st/2nd of right/left/right -> sir
        "match": "yell (dye) head",
        "answer_text": "sir",
        "explanation": (
            "Answer:\n\nThe middle word takes: last letter of right word, 1st letter of left "
            "word, 2nd letter of right word. "
            "yell (dye) head: d(last of head), y(1st of yell), e(2nd of head) = dye. "
            "idea (?) iris: s(last of iris), i(1st of idea), r(2nd of iris) = sir."
        ),
    },
    {
        # Q19: Duplicate of Q9 (any+one=anyone) - handled by dedup
        "match": "any",
        "answer_text": "any, one",
        "explanation": (
            "Answer:\n\n\u2018anyone\u2019 is the only correctly spelled word that can be made."
        ),
    },
    {
        # Q20: gait(girl)hurl -> positions 1,3 of left; 3,4 of right -> dawn
        "match": "gait (girl) hurl",
        "answer_text": "dawn",
        "explanation": (
            "Answer:\n\nThe middle word takes: 1st and 3rd letters of the left word, "
            "3rd and 4th letters of the right word. "
            "gait (girl) hurl: g(1st), i(3rd) from gait; r(3rd), l(4th) from hurl = girl. "
            "draw (?) down: d(1st), a(3rd) from draw; w(3rd), n(4th) from down = dawn."
        ),
    },
    {
        # Q11 metadata: be+low=below (A, E answer)
        "match": "be",
        "answer_text": "be, low",
        "explanation": (
            "Answer:\n\n\u2018below\u2019 is the only correctly spelled word that can be made."
        ),
    },
]


def find_fix(question: dict, fixes: list[dict]) -> dict | None:
    """Find a manual fix by searching for match substring in text or options."""
    text = normalize_text(question.get("content", {}).get("text", ""))
    opts = question.get("content", {}).get("options", [])
    opts_text = " ".join(opts)

    for fix in fixes:
        match = fix["match"]
        if match in text or match in opts_text:
            return fix
    return None


def convert_multi_answer(answer_val: str, options: list[str]) -> str:
    """Convert multi-select letter answers like 'B, D' to option text."""
    parts = [p.strip() for p in answer_val.split(",")]
    if all(p in LETTER_TO_IDX for p in parts):
        texts = []
        for p in parts:
            idx = LETTER_TO_IDX[p]
            if idx < len(options):
                texts.append(options[idx])
        if texts:
            return ", ".join(texts)
    return answer_val


def is_multi_select_letter(answer_val: str) -> bool:
    """Check if answer looks like 'B, D' (multi-select letters)."""
    if "," not in str(answer_val):
        return False
    parts = [p.strip() for p in str(answer_val).split(",")]
    return len(parts) >= 2 and all(p in LETTER_TO_IDX for p in parts)


def fix_answer(question: dict, fixes: list[dict]) -> dict:
    """Fix a single question's answer."""
    content = question.get("content", {})
    answer = question.get("answer", {})
    options = content.get("options", [])
    answer_val = answer.get("value", "")

    if not options:
        return question

    # Case 1: Multi-select letter answer like "B, D"
    if is_multi_select_letter(answer_val):
        answer["value"] = convert_multi_answer(answer_val, options)
        question["answer"] = answer
        return question

    # Case 2: Single letter answer - convert to option text
    if answer_val in LETTER_TO_IDX:
        idx = LETTER_TO_IDX[answer_val]
        if idx < len(options):
            answer["value"] = options[idx]
            question["answer"] = answer
            return question

    # Case 3: Unknown answer - look up manual fix
    if answer_val in ("Unknown", "", None):
        fix = find_fix(question, fixes)
        if fix:
            answer["value"] = fix["answer_text"]
            question["answer"] = answer
            question["explanation"] = fix["explanation"]
            return question

    return question


def deduplicate_questions(questions: list[dict], subjects: set[str]) -> tuple[list, dict]:
    """Remove duplicate questions (same text, different option order) for given subjects."""
    seen_texts: dict[str, set] = {}
    unique = []
    removed: dict[str, int] = {}

    for q in questions:
        subj = q.get("subject", "")
        if subj not in subjects:
            unique.append(q)
            continue

        text = normalize_text(q.get("content", {}).get("text", ""))
        if subj not in seen_texts:
            seen_texts[subj] = set()

        if text in seen_texts[subj]:
            removed[subj] = removed.get(subj, 0) + 1
            continue
        seen_texts[subj].add(text)
        unique.append(q)

    return unique, removed


def is_known_multi_select(question: dict) -> bool:
    """Check if a question is multi-select based on its format/text."""
    text = question.get("content", {}).get("text", "")
    # VR multi-select patterns
    multi_patterns = [
        "Select a word from the first column",
        "Choose two words, one from each",
        "Find the two words that are not related",
    ]
    return any(p in text for p in multi_patterns)


def verify_answers(questions: list[dict], subjects: set[str]) -> int:
    """Verify all answers are option text, not letters or Unknown."""
    issues = 0
    for q in questions:
        subj = q.get("subject", "")
        if subj not in subjects:
            continue
        ans_val = q.get("answer", {}).get("value", "")
        opts = q.get("content", {}).get("options", [])

        if ans_val in ("Unknown", "", None):
            text = normalize_text(q.get("content", {}).get("text", ""))[:80]
            print(f"  STILL UNKNOWN [{subj}]: {text}")
            issues += 1
        elif ans_val in LETTER_TO_IDX:
            text = normalize_text(q.get("content", {}).get("text", ""))[:60]
            print(f"  STILL LETTER [{subj}]: ans={ans_val} | {text}")
            issues += 1
        elif is_multi_select_letter(ans_val):
            text = normalize_text(q.get("content", {}).get("text", ""))[:60]
            print(f"  STILL MULTI-LETTER [{subj}]: ans={ans_val} | {text}")
            issues += 1
        elif opts:
            # For multi-select answers, check each part
            if is_known_multi_select(q) and ", " in ans_val:
                parts = [p.strip() for p in ans_val.split(", ")]
                for part in parts:
                    if part not in opts:
                        text = normalize_text(q.get("content", {}).get("text", ""))[:60]
                        print(f"  NOT IN OPTIONS [{subj}]: '{part}' | {text}")
                        issues += 1
            elif ans_val not in opts:
                text = normalize_text(q.get("content", {}).get("text", ""))[:60]
                print(f"  NOT IN OPTIONS [{subj}]: '{ans_val}' | {text}")
                issues += 1

    return issues


def main():
    with open(DUMP_FILE) as f:
        data = json.load(f)

    questions = data if isinstance(data, list) else data.get("questions", [])

    subjects = {"english", "verbal_reasoning"}
    counts_before = {}
    for subj in subjects:
        counts_before[subj] = sum(1 for q in questions if q.get("subject") == subj)

    print(f"Before fix: {len(questions)} total")
    for subj, cnt in sorted(counts_before.items()):
        print(f"  {subj}: {cnt}")

    # Step 1: Fix answers
    for q in questions:
        subj = q.get("subject", "")
        if subj == "english":
            fix_answer(q, ENGLISH_FIXES)
        elif subj == "verbal_reasoning":
            fix_answer(q, VR_FIXES)

    # Step 2: Deduplicate
    questions, removed = deduplicate_questions(questions, subjects)

    print(f"\nAfter fix: {len(questions)} total")
    for subj in sorted(subjects):
        cnt = sum(1 for q in questions if q.get("subject") == subj)
        rem = removed.get(subj, 0)
        print(f"  {subj}: {cnt} (removed {rem} duplicates)")

    # Step 3: Verify
    print("\nVerification:")
    issues = verify_answers(questions, subjects)
    if issues == 0:
        print("  All English and VR answers verified OK!")

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
