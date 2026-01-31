"""Audit and fix all metadata.json files, then rebuild deployment_dump.json.

Comprehensive fixes based on manual review of all 538 questions:

  Maths:   Remove garbled GL questions (fractions, merged text, leaked coords,
           missing numbers, em-dash options, letter-only visual without images).
           Fix E-unit leak pattern, strip page markers, clean nbsp.
  VR:      Remove Unknown answers, answer-option mismatches, < 5 options.
           Strip page markers.
  English: Remove Unknown answers, broken "B C D" options, leaked section headers.
           Fix 13 wrong GL comprehension answers. Clean leaked answer text.
  NVR:     Keep odd-one-out questions (no question image but valid option images).

Usage:
    uv run python backend/scripts/fix_all_questions.py
"""

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
IMAGES_DIR = PROJECT_ROOT / "backend" / "data" / "images"

LETTERS = "ABCDEFGH"

# ---------------------------------------------------------------------------
# Known wrong GL English comprehension answers (metadata index -> correct letter)
# Verified by reading each question against the passage text.
# ---------------------------------------------------------------------------
ENGLISH_ANSWER_FIXES = {
    # English 1 (Swiss Family Robinson)
    51: "C",   # "prisoners set free": trapped in house by storms, not cave
    55: "C",   # "habitable" = able to live in, not "dried out by itself"
    56: "C",   # supplies were in their tent, not a cellar
    57: "E",   # "spread things in sun to dry", not "shook water off"
    58: "D",   # "irreparable" = impossible to repair, not "easy to repair"
    59: "B",   # "quarters" = lodgings, not stables
    61: "E",   # goal was winter accommodation, not "look-out point"
    62: "D",   # smaller cave -> "storage space for supplies", not "house for dog"
    63: "D",   # "almost insurmountable" = nearly impossible, not "easy"
    64: "C",   # "minds bent on success" = determined, not "indifferent"
    69: "D",   # heavily/vigorously/quickly are adverbs, not adjectives
    # English 2 (Secret Garden)
    119: "E",  # "untrimmed ivy" suggests neglect, not "glossy dark green leaves"
    125: "D",  # mysteriously/carefully/thickly/adorably are adverbs, not adjectives
}

# Metadata indices with leaked text that should be cleaned from answer field
ENGLISH_ANSWER_CLEAN = {
    60: "B",   # "B Hippos" -> "B" (next section text leaked into answer)
    113: "A",  # "A A Ghostly Encounter" -> "A" (passage title leaked)
}


def resolve_answer(answer_raw: str, options: list[str]) -> str:
    """Resolve letter-based answer to option value."""
    if not options:
        return answer_raw

    # Single letter answer
    if answer_raw in LETTERS:
        idx = LETTERS.index(answer_raw)
        if idx < len(options):
            return options[idx]

    # "B Hippos" format - letter + space + leaked text
    if len(str(answer_raw)) > 1 and answer_raw[0] in LETTERS and answer_raw[1] == " ":
        idx = LETTERS.index(answer_raw[0])
        if idx < len(options):
            return options[idx]

    # Multi-answer "B, D"
    if ", " in str(answer_raw):
        parts = [c.strip() for c in str(answer_raw).split(", ")]
        if all(c in LETTERS for c in parts):
            indices = [LETTERS.index(c) for c in parts]
            return ", ".join(options[i] for i in indices if i < len(options))

    return answer_raw


def answer_in_options(answer_value: str, options: list[str]) -> bool:
    """Check if resolved answer value exists in options list."""
    opt_strs = [str(o).strip() for o in options]
    ans = str(answer_value).strip()

    # Direct match
    if ans in opt_strs:
        return True

    # Multi-answer: each part must be in options
    if ", " in ans:
        parts = [p.strip() for p in ans.split(", ")]
        return all(p in opt_strs for p in parts)

    # Normalized match (case-insensitive, whitespace-collapsed)
    ans_norm = re.sub(r"\s+", " ", ans.lower())
    for o in opt_strs:
        if re.sub(r"\s+", " ", o.lower()) == ans_norm:
            return True

    return False


# ---------------------------------------------------------------------------
# Maths cleanup
# ---------------------------------------------------------------------------


def fix_maths(data: list[dict]) -> tuple[list[dict], dict]:
    """Fix maths metadata. Returns (cleaned_data, stats)."""
    stats = {
        "total": len(data),
        "removed_unknown": 0,
        "removed_single_option": 0,
        "removed_garbled": 0,
        "removed_merged": 0,
        "removed_no_options": 0,
        "cleaned_text": 0,
        "cleaned_opts": 0,
        "cleaned_nbsp": 0,
        "kept": 0,
    }

    result = []
    for q in data:
        text = q.get("text", "")
        opts = q.get("options", [])
        source = q.get("source", "")
        has_img = bool(q.get("question_image") or q.get("question_images"))
        is_gl = "GL" in source

        # --- REMOVAL FILTERS ---

        # 1. Remove Unknown answer
        if q.get("answer") == "Unknown":
            stats["removed_unknown"] += 1
            continue

        # 2. Remove single option (broken extraction)
        if len(opts) <= 1:
            stats["removed_single_option"] += 1
            continue

        # 3. Remove garbled fraction options (newlines in options)
        if any("\n" in str(o) for o in opts):
            stats["removed_garbled"] += 1
            continue

        # 4. Remove garbled fraction text (consecutive single-char newlines)
        if re.search(r"(?:\n.){4,}", text):
            stats["removed_garbled"] += 1
            continue

        # 5. Remove em-dash fraction options (GL PDF fraction rendering failure)
        #    Pattern: options like "-- 3", "-- 1", "--" where fractions weren't extracted
        em_dash_opts = sum(1 for o in opts if re.match(r"^[—\-]{1,2}\s*\d*$", str(o).strip()))
        if em_dash_opts >= 3:
            stats["removed_garbled"] += 1
            continue

        # 6. Remove visual questions with letter-only options but no image
        #    Catches both "A","B","C" and "a)","b)","c)" formats
        if not has_img and opts:
            all_letter_labels = all(
                re.match(r"^[a-eA-E][\).]?$", str(o).strip()) for o in opts
            )
            if all_letter_labels:
                stats["removed_no_options"] += 1
                continue

        # 7. Remove questions with garbled text containing leaked option markers
        #    GL extraction artifact: "÷ = C . D .5" or "a = ? C -- D 2 E --"
        if is_gl and re.search(r"[?=]\s*[A-E]\s*[.—\-]", text):
            stats["removed_garbled"] += 1
            continue

        # 8. Remove questions with "stands for N" pictogram garbling
        if "stands for" in text.lower() and ("table" in text.lower() or "Dock" in text):
            stats["removed_garbled"] += 1
            continue

        # 9. Remove questions with coordinate grid numbers leaked into text
        if re.search(r"\b7\s+6\s+5\s+4\s+3\s+2\s+1\b", text):
            stats["removed_garbled"] += 1
            continue
        if re.search(r"\b1\s+2\s+3\s+4\s+5\s+6\s+7\b", text):
            stats["removed_garbled"] += 1
            continue

        # 10. Remove questions with "g N" garbled coordinate notation
        if is_gl and re.search(r"\bg\s+\d", text) and "translation" in text.lower():
            stats["removed_garbled"] += 1
            continue

        # 11. Remove questions with missing numbers in text
        #     "what does the stand for?" or "the answer is . What number"
        if is_gl and ("the stand for" in text.lower() or "the answer is ." in text.lower()):
            stats["removed_garbled"] += 1
            continue

        # 12. Remove "What is 32 ?" (garbled superscript 3^2)
        if "is 32 ?" in text or "is 32?" in text:
            # Only if options suggest it was 3^2 (answer 9)
            if "9" in [str(o).strip() for o in opts]:
                stats["removed_garbled"] += 1
                continue

        # 13. Remove "weather for 1 on one day" (garbled chart reference)
        if "weather for 1" in text:
            stats["removed_garbled"] += 1
            continue

        # 14. Remove "Share 2 into N equal parts" (garbled fraction)
        if re.search(r"Share\s+\d\s+into\s+\d", text) and is_gl:
            stats["removed_garbled"] += 1
            continue

        # 15. Remove garbled fraction equations: "3 = 4 8" without proper formatting
        if re.search(r"\b\d\s+=\s+\d\s+\d\b", text) and is_gl and "box" in text.lower():
            stats["removed_garbled"] += 1
            continue

        # 16. Remove "subtracts and then multiplies" (missing operand number)
        if "subtracts and then multiplies" in text and is_gl:
            stats["removed_garbled"] += 1
            continue

        # 17. Remove questions with dimensions in text that should be in image
        if re.search(r"\d+\.\d+m\s+\d+\.\d+m", text) and is_gl:
            stats["removed_garbled"] += 1
            continue

        # 18. Remove "What is 1.7 as a fraction? C 0" (garbled fraction question)
        if re.search(r"as a fraction\?\s*[A-E]\s*\d", text):
            stats["removed_garbled"] += 1
            continue

        # --- TEXT CLEANING ---

        text_clean = text

        # Strip page markers
        text_clean = re.sub(
            r"\s*Page\s+\d+\s*Please go on to the next page\s*>{2,}", "", text_clean
        )
        text_clean = re.sub(r"\s*END OF FAMILIARISATION PAPER.*$", "", text_clean)
        text_clean = re.sub(r"\s*Copyright GL Asse.*$", "", text_clean)
        text_clean = re.sub(r"\s+E\s+Page\s+\d+\s*Please go on.*$", "", text_clean)
        text_clean = re.sub(r"\s+E\s+Page\s+.*$", "", text_clean)
        text_clean = re.sub(r"\s+E\s*$", "", text_clean)
        text_clean = re.sub(r"\s+E\s+\d+[\s\d,\.]+$", "", text_clean)
        text_clean = re.sub(r"\s*>{3,}.*$", "", text_clean)

        # Strip leaked fraction numbers after question text
        # e.g. "What fraction... shaded? E 10 3 8 4 11"
        text_clean = re.sub(r"\?\s+E\s+[\d\s]+$", "?", text_clean)

        if text_clean != text:
            stats["cleaned_text"] += 1
            text = text_clean

        # Fix "E <text>" leaked into question text from option E
        # The GL extraction sometimes splits option E across the question text
        # and the option field. Reconstruct when safe; strip always.
        e_leak = re.search(r"(\?)\s+E\s+(.+)$", text)
        if e_leak and len(opts) >= 5:
            leaked = e_leak.group(2).strip()
            last_opt = str(opts[4]).strip()
            combined = f"{last_opt} {leaked}" if last_opt else leaked
            combined_len = len(combined)

            # Determine if reconstruction is safe:
            # - No option markers in leaked text (indicates merged next question)
            # - No "Page" or ">>>" (page navigation artifacts)
            # - Combined length reasonable (< 80 chars)
            has_option_markers = bool(
                re.search(r"\b[A-E]\s+\d+\s+[A-E]\s+\d+", leaked)
                or re.search(r"\bPage\b", leaked)
                or ">>>" in leaked
            )
            safe_to_reconstruct = (
                not has_option_markers
                and combined_len < 80
            )
            other_opts_longer = any(
                len(str(opts[j]).strip()) > len(last_opt) * 1.5
                for j in range(min(4, len(opts)))
            )

            # Always strip the leaked text from question text
            text = text[: e_leak.start()] + "?"
            stats["cleaned_text"] += 1

            # Reconstruct option E if safe and it appears truncated
            if safe_to_reconstruct and other_opts_longer:
                opts = list(opts)
                opts[4] = combined
                stats["cleaned_opts"] += 1

        # --- MERGED TEXT DETECTION (after cleaning) ---

        is_merged = (
            (is_gl and len(text.strip()) > 150)
            or len(text.strip()) > 250
            or re.search(r"\b[A-E]\s+\d+\s+[A-E]\s+\d+", text)
            or re.search(r"\bE\s+Page\b", text)
            or ">>>" in text
            or re.search(r"\bE\s+\d+\s+\d+\s+\d+", text)
        )
        if is_merged:
            stats["removed_merged"] += 1
            continue

        # Remove very short text (< 10 chars)
        if len(text.strip()) < 10:
            stats["removed_merged"] += 1
            continue

        # --- OPTION CLEANING ---

        cleaned_opts = []
        opts_modified = False
        for o in opts:
            o_str = str(o)
            # Clean nbsp
            if "\xa0" in o_str:
                o_str = o_str.replace("\xa0", " ")
                opts_modified = True
            # Strip "Page N" from end of options
            o_clean = re.sub(r"\s*Page\s+\d+\s*$", "", o_str)
            if o_clean != o_str:
                o_str = o_clean
                opts_modified = True
            # Strip trailing digit junk from options (e.g. "180 coins 2 6 5")
            # Only if the option has a clear value followed by unrelated numbers
            if is_gl and re.search(r"(\w+)\s+\d+\s+\d+\s+\d+$", o_str):
                o_clean = re.sub(r"\s+\d+\s+\d+\s+\d+$", "", o_str)
                if len(o_clean) > 2:
                    o_str = o_clean
                    opts_modified = True
            cleaned_opts.append(o_str)

        if opts_modified:
            stats["cleaned_opts"] += 1

        # Remove questions where any option is excessively long (merged content)
        if any(len(str(o)) > 80 for o in cleaned_opts):
            stats["removed_merged"] += 1
            continue

        # Clean nbsp in text
        if "\xa0" in text:
            text = text.replace("\xa0", " ")
            stats["cleaned_nbsp"] += 1

        # --- ANSWER VERIFICATION ---

        answer_value = resolve_answer(q.get("answer", ""), cleaned_opts)
        if not answer_in_options(answer_value, cleaned_opts):
            if not has_img:
                stats["removed_no_options"] += 1
                continue

        q_out = dict(q)
        q_out["text"] = text
        q_out["options"] = cleaned_opts
        result.append(q_out)
        stats["kept"] += 1

    return result, stats


# ---------------------------------------------------------------------------
# VR cleanup
# ---------------------------------------------------------------------------


def fix_vr(data: list[dict]) -> tuple[list[dict], dict]:
    """Fix verbal reasoning metadata."""
    stats = {
        "total": len(data),
        "removed_unknown": 0,
        "removed_answer_mismatch": 0,
        "removed_few_options": 0,
        "cleaned_page_text": 0,
        "cleaned_nbsp": 0,
        "kept": 0,
    }

    result = []
    for q in data:
        opts = q.get("options", [])
        answer_raw = q.get("answer", "")

        # 1. Remove Unknown answers
        if answer_raw == "Unknown":
            stats["removed_unknown"] += 1
            continue

        # 2. Remove non-standard answer codes (e.g. "NC")
        if answer_raw not in LETTERS and not any(
            c in LETTERS for c in str(answer_raw).split(", ")
        ):
            # Check if it's a direct option match
            if not answer_in_options(answer_raw, opts):
                stats["removed_answer_mismatch"] += 1
                continue

        # 3. Remove if fewer than 4 options (GL VR should have 5)
        if len(opts) < 4:
            stats["removed_few_options"] += 1
            continue

        # 4. Resolve answer and check it's in options
        answer_value = resolve_answer(answer_raw, opts)
        if not answer_in_options(answer_value, opts):
            stats["removed_answer_mismatch"] += 1
            continue

        q_out = dict(q)
        text = q_out.get("text", "")

        # 5. Strip page markers
        text_clean = re.sub(
            r"\s*Page\s+\d+\s*Please go on to the next page\s*>{2,}", "", text
        )
        text_clean = re.sub(r"\s*>{3,}.*$", "", text_clean)
        if text_clean != text:
            text = text_clean
            stats["cleaned_page_text"] += 1

        # 6. Clean nbsp
        if "\xa0" in text:
            text = text.replace("\xa0", " ")
            stats["cleaned_nbsp"] += 1

        q_out["text"] = text
        result.append(q_out)
        stats["kept"] += 1

    return result, stats


# ---------------------------------------------------------------------------
# English cleanup
# ---------------------------------------------------------------------------


def fix_english(data: list[dict]) -> tuple[list[dict], dict]:
    """Fix English metadata."""
    stats = {
        "total": len(data),
        "removed_unknown": 0,
        "removed_broken_options": 0,
        "removed_leaked_section": 0,
        "fixed_answers": 0,
        "cleaned_answer": 0,
        "cleaned_text": 0,
        "cleaned_nbsp": 0,
        "kept": 0,
    }

    result = []
    for i, q in enumerate(data):
        opts = q.get("options", [])
        answer_raw = q.get("answer", "")

        # 1. Remove Unknown answers
        if answer_raw == "Unknown":
            stats["removed_unknown"] += 1
            continue

        # 2. Remove broken GL extraction: options are just "B C D" or "B C D E"
        if opts and all(
            re.match(r"^[A-E](\s+[A-E])*$", str(o).strip()) for o in opts
        ):
            stats["removed_broken_options"] += 1
            continue

        # 3. Remove if < 3 real options
        if len(opts) < 3:
            stats["removed_broken_options"] += 1
            continue

        q_out = dict(q)
        text = q_out.get("text", "")

        # 4. Remove questions with leaked section headers in text
        #    e.g. "Spelling Exercises In these sentences..."
        #    or "Punctuation In these sentences..."
        if re.search(
            r"(Spelling Exercises|Punctuation)\s+In these sentences", text
        ):
            stats["removed_leaked_section"] += 1
            continue

        # 5. Fix known wrong answers
        if i in ENGLISH_ANSWER_FIXES:
            q_out["answer"] = ENGLISH_ANSWER_FIXES[i]
            stats["fixed_answers"] += 1

        # 6. Clean leaked text from answer field
        if i in ENGLISH_ANSWER_CLEAN:
            q_out["answer"] = ENGLISH_ANSWER_CLEAN[i]
            stats["cleaned_answer"] += 1

        # 7. Clean leaked trailing words from question text
        #    Pattern: question ending in "?" or ")" followed by a stray word
        #    e.g. "Why? (lines 2-3) been dropped." or "attitude? succeed."
        text_clean = text
        # Remove trailing leaked word after closing paren or question mark
        # Only if it's a short stray fragment (< 20 chars after the marker)
        text_clean = re.sub(
            r"(\?\s*(?:\([^)]+\))?\s*)\b[a-z]\w*\.?\s*$", r"\1", text_clean
        )
        # Remove "of time." "expect." "strength." trailing fragments
        text_clean = re.sub(r"\b(of time|expect|succeed|strength)\.\s*$", "", text_clean)

        if text_clean != text:
            text = text_clean.rstrip()
            stats["cleaned_text"] += 1

        # 8. Clean nbsp
        if "\xa0" in text:
            text = text.replace("\xa0", " ")
            stats["cleaned_nbsp"] += 1

        q_out["text"] = text
        result.append(q_out)
        stats["kept"] += 1

    return result, stats


# ---------------------------------------------------------------------------
# NVR cleanup
# ---------------------------------------------------------------------------


def fix_nvr(data: list[dict]) -> tuple[list[dict], dict]:
    """Fix NVR metadata."""
    stats = {
        "total": len(data),
        "removed_missing_images": 0,
        "kept": 0,
    }

    img_dir = IMAGES_DIR / "granular_non_verbal_reasoning"
    result = []
    for q in data:
        missing = False
        for img in q.get("question_images", []):
            if img and not (img_dir / img).exists():
                missing = True
                break
        for img in q.get("images", []):
            if img and not (img_dir / img).exists():
                missing = True
                break

        if missing:
            stats["removed_missing_images"] += 1
            continue

        result.append(q)
        stats["kept"] += 1

    return result, stats


# ---------------------------------------------------------------------------
# Validation pass (runs on rebuilt dump)
# ---------------------------------------------------------------------------


def validate_dump(dump: list[dict]) -> list[str]:
    """Validate every question in the dump. Returns list of issues."""
    issues = []
    for i, q in enumerate(dump):
        subj = q.get("subject", "")
        content = q.get("content", {})
        text = content.get("text", "")
        opts = content.get("options", [])
        answer_val = q.get("answer", {}).get("value", "")

        # 1. Answer in options (skip NVR)
        if subj != "non_verbal_reasoning":
            if answer_val and opts:
                opt_strs = [str(o).strip() for o in opts]
                opt_lower = [o.lower() for o in opt_strs]
                ans = str(answer_val).strip()

                if ans in opt_strs or ans.lower() in opt_lower:
                    pass
                else:
                    ans_parts = [p.strip() for p in ans.split(", ")]
                    if not all(
                        p in opt_strs or p.lower() in opt_lower for p in ans_parts
                    ):
                        issues.append(
                            f"[{i}] {subj}: answer {ans!r} not in opts {opt_strs[:3]}..."
                        )

        # 2. No newlines in options
        for j, o in enumerate(opts):
            if "\n" in str(o):
                issues.append(f"[{i}] {subj}: opt {j} newline: {repr(str(o)[:40])}")

        # 3. No page markers in text
        if re.search(r"Page\s+\d+\s*Please go on", text):
            issues.append(f"[{i}] {subj}: page marker")

        # 4. No garbled fraction text
        if re.search(r"(?:\n.){4,}", text):
            issues.append(f"[{i}] {subj}: garbled fraction text")

        # 5. No trailing "E <word>" artifact
        if re.search(r"\?\s+E\s+\w+\s*$", text):
            issues.append(f"[{i}] {subj}: trailing E artifact")

        # 6. Text length (skip NVR)
        if subj != "non_verbal_reasoning" and len(text.strip()) < 10:
            issues.append(f"[{i}] {subj}: text too short ({len(text.strip())}ch)")

        # 7. NVR must have images
        if subj == "non_verbal_reasoning":
            if not (content.get("image_url") or content.get("option_images")):
                issues.append(f"[{i}] NVR: no images")

        # 8. Options count
        if len(opts) < 2:
            issues.append(f"[{i}] {subj}: only {len(opts)} opt(s)")

        # 9. Maths: no letter-only options without images
        if subj == "maths" and not content.get("image_url"):
            if opts and all(re.match(r"^[a-eA-E][\).]?$", str(o).strip()) for o in opts):
                issues.append(f"[{i}] maths: letter-only opts no image")

        # 10. Em-dash fraction options
        if subj == "maths":
            em_count = sum(
                1 for o in opts if re.match(r"^[—\-]{1,2}\s*\d*$", str(o).strip())
            )
            if em_count >= 3:
                issues.append(f"[{i}] maths: em-dash fraction opts")

        # 11. Garbled text indicators
        if subj == "maths":
            if "the stand for" in text.lower():
                issues.append(f"[{i}] maths: missing number in text")
            if "stands for" in text.lower() and "table" in text.lower():
                issues.append(f"[{i}] maths: garbled pictogram")

        # 12. Leaked section headers in English
        if subj == "english":
            if re.search(r"(Spelling Exercises|Punctuation)\s+In these", text):
                issues.append(f"[{i}] english: leaked section header")

        # 13. Options with 'Page' text
        for j, o in enumerate(opts):
            if "Page " in str(o) and re.search(r"Page\s+\d+", str(o)):
                issues.append(f"[{i}] {subj}: 'Page N' in opt {j}")

    return issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print("=" * 60)
    print("Question Content Audit and Fix (Comprehensive)")
    print("=" * 60)

    all_stats = {}

    # --- Maths ---
    path = IMAGES_DIR / "granular_maths" / "metadata.json"
    print(f"\n--- Maths: {path} ---")
    with open(path) as f:
        maths_data = json.load(f)
    maths_fixed, maths_stats = fix_maths(maths_data)
    all_stats["maths"] = maths_stats
    print(f"  Before: {maths_stats['total']}, After: {maths_stats['kept']}")
    for k, v in maths_stats.items():
        if k not in ("total", "kept") and v > 0:
            print(f"    {k}: {v}")
    with open(path, "w") as f:
        json.dump(maths_fixed, f, indent=2, ensure_ascii=False)
    print(f"  Wrote {len(maths_fixed)} entries to {path.name}")

    # --- VR ---
    path = IMAGES_DIR / "granular_verbal_reasoning" / "metadata.json"
    print(f"\n--- VR: {path} ---")
    with open(path) as f:
        vr_data = json.load(f)
    vr_fixed, vr_stats = fix_vr(vr_data)
    all_stats["vr"] = vr_stats
    print(f"  Before: {vr_stats['total']}, After: {vr_stats['kept']}")
    for k, v in vr_stats.items():
        if k not in ("total", "kept") and v > 0:
            print(f"    {k}: {v}")
    with open(path, "w") as f:
        json.dump(vr_fixed, f, indent=2, ensure_ascii=False)
    print(f"  Wrote {len(vr_fixed)} entries to {path.name}")

    # --- English ---
    path = IMAGES_DIR / "granular_english" / "metadata.json"
    print(f"\n--- English: {path} ---")
    with open(path) as f:
        eng_data = json.load(f)
    eng_fixed, eng_stats = fix_english(eng_data)
    all_stats["english"] = eng_stats
    print(f"  Before: {eng_stats['total']}, After: {eng_stats['kept']}")
    for k, v in eng_stats.items():
        if k not in ("total", "kept") and v > 0:
            print(f"    {k}: {v}")
    with open(path, "w") as f:
        json.dump(eng_fixed, f, indent=2, ensure_ascii=False)
    print(f"  Wrote {len(eng_fixed)} entries to {path.name}")

    # --- NVR ---
    path = IMAGES_DIR / "granular_non_verbal_reasoning" / "metadata.json"
    print(f"\n--- NVR: {path} ---")
    with open(path) as f:
        nvr_data = json.load(f)
    nvr_fixed, nvr_stats = fix_nvr(nvr_data)
    all_stats["nvr"] = nvr_stats
    print(f"  Before: {nvr_stats['total']}, After: {nvr_stats['kept']}")
    for k, v in nvr_stats.items():
        if k not in ("total", "kept") and v > 0:
            print(f"    {k}: {v}")
    with open(path, "w") as f:
        json.dump(nvr_fixed, f, indent=2, ensure_ascii=False)
    print(f"  Wrote {len(nvr_fixed)} entries to {path.name}")

    # --- Rebuild dump ---
    print(f"\n{'=' * 60}")
    print("Rebuilding deployment_dump.json...")
    print("=" * 60)

    sys.path.insert(0, str(Path(__file__).parent))
    from build_verified_dump import build_dump

    dump = build_dump()

    # --- Validate ---
    print(f"\n{'=' * 60}")
    print("Validation Pass")
    print("=" * 60)
    issues = validate_dump(dump)
    if issues:
        print(f"\n  FOUND {len(issues)} ISSUES:")
        for issue in issues:
            print(f"    {issue}")
    else:
        print("\n  ALL QUESTIONS PASSED VALIDATION")

    # --- Summary ---
    print(f"\n{'=' * 60}")
    print("Fix Summary")
    print("=" * 60)
    total_before = sum(s["total"] for s in all_stats.values())
    total_after = sum(s["kept"] for s in all_stats.values())
    print(f"  Metadata before: {total_before}")
    print(f"  Metadata after:  {total_after}")
    print(f"  Removed:         {total_before - total_after}")
    print(f"  Dump questions:  {len(dump)}")

    return len(issues)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(1 if exit_code > 0 else 0)
