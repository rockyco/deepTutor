"""Audit and fix all metadata.json files, then rebuild deployment_dump.json.

Fixes:
  Maths:   Remove broken GL questions (page markers, merged text, single options),
           remove garbled fraction duplicates from CGP.
  VR:      Remove questions with Unknown answers or answer-option mismatches.
  English: Remove broken GL questions (B C D only options, Unknown answers).
  NVR:     Keep odd-one-out questions (no question image but valid option images).

Usage:
    uv run python backend/scripts/fix_all_questions.py
"""

import json
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
IMAGES_DIR = PROJECT_ROOT / "backend" / "data" / "images"

LETTERS = "ABCDEFGH"


def resolve_answer(answer_raw: str, options: list[str]) -> str:
    """Resolve letter-based answer to option value."""
    if not options:
        return answer_raw

    # Single letter answer
    if answer_raw in LETTERS:
        idx = LETTERS.index(answer_raw)
        if idx < len(options):
            return options[idx]

    # "B Hippos" format
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
        "removed_page_markers": 0,
        "removed_merged": 0,
        "removed_single_option": 0,
        "removed_garbled_fractions": 0,
        "removed_no_options": 0,
        "cleaned_page_text": 0,
        "cleaned_nbsp": 0,
        "kept": 0,
    }

    result = []
    for q in data:
        text = q.get("text", "")
        opts = q.get("options", [])
        source = q.get("source", "")
        has_img = bool(q.get("question_image") or q.get("question_images"))

        # 1. Remove questions with Unknown answer
        if q.get("answer") == "Unknown":
            stats["removed_no_options"] += 1
            continue

        # 2. Remove questions with single option (broken GL extraction)
        if len(opts) <= 1:
            stats["removed_single_option"] += 1
            continue

        # 3. Remove garbled fraction options (newlines in options)
        if any("\n" in str(o) for o in opts):
            stats["removed_garbled_fractions"] += 1
            continue

        # 3b. Remove garbled fraction text (single chars on consecutive newlines)
        if re.search(r"(?:\n.){4,}", text):
            stats["removed_garbled_fractions"] += 1
            continue

        # 3c. Remove visual questions with letter-only options but no image
        #     (the actual options are in an image that wasn't extracted)
        if (
            not has_img
            and opts
            and all(re.match(r"^[A-E]$", str(o).strip()) for o in opts)
        ):
            stats["removed_no_options"] += 1
            continue

        # 4. Strip page markers from text
        text_clean = text
        text_clean = re.sub(
            r"\s*Page\s+\d+\s*Please go on to the next page\s*>{2,}", "", text_clean
        )
        text_clean = re.sub(r"\s*END OF FAMILIARISATION PAPER.*$", "", text_clean)
        text_clean = re.sub(r"\s*Copyright GL Asse.*$", "", text_clean)
        # Strip trailing "E Page ..." patterns (partial page markers)
        text_clean = re.sub(r"\s+E\s+Page\s+\d+\s*Please go on.*$", "", text_clean)
        text_clean = re.sub(r"\s+E\s+Page\s+.*$", "", text_clean)
        # Strip trailing single letter artifacts after page marker removal
        text_clean = re.sub(r"\s+E\s*$", "", text_clean)
        # Strip trailing "E <num> <num>..." (answer choices from next question leaked in)
        text_clean = re.sub(r"\s+E\s+\d+[\s\d,\.]+$", "", text_clean)
        # Strip page navigation arrows
        text_clean = re.sub(r"\s*>{3,}.*$", "", text_clean)

        if text_clean != text:
            stats["cleaned_page_text"] += 1
            text = text_clean

        # 4b. Fix "E <unit>" leaked into question text from option E
        #     GL extraction artifact: option E's prefix leaked into question text.
        #     E.g. "How tall? E m" with opts[4]="1.603" -> fix to "1.603 m"
        #     Only fix when leaked text looks like a unit suffix (not a number).
        e_leak = re.search(r"(\?)\s+E\s+(.+)$", text)
        if e_leak and len(opts) >= 5:
            leaked = e_leak.group(2).strip()
            last_opt = str(opts[4]).strip()
            # Only reconstruct if leaked text is a plausible suffix (not starting with digits)
            # and option E looks truncated vs other options
            is_unit_suffix = not re.match(r"^\d", leaked)
            other_opts_longer = any(
                len(str(opts[j]).strip()) > len(last_opt) * 1.5
                for j in range(min(4, len(opts)))
            )
            # Strip the leaked text from question text
            text = text[: e_leak.start()] + "?"
            stats["cleaned_page_text"] += 1
            if is_unit_suffix and other_opts_longer:
                # Reconstruct: "9" + "boys" -> "9 boys"
                opts = list(opts)
                opts[4] = f"{last_opt} {leaked}" if last_opt else leaked

        # 5. Remove merged/garbled questions
        is_gl = "GL" in source
        is_merged = (
            # GL questions: stricter - 150 chars usually means merged
            (is_gl and len(text.strip()) > 150)
            # Any source: absolute limit
            or len(text.strip()) > 250
            # Merged question indicators (answer choices from adjacent question)
            or re.search(r"\b[A-E]\s+\d+\s+[A-E]\s+\d+", text)  # "A 3 B 5"
            or re.search(r"\bE\s+Page\b", text)
            or ">>>" in text
            or re.search(r"\bE\s+\d+\s+\d+\s+\d+", text)  # "E 33 9 36"
        )
        if is_merged:
            stats["removed_merged"] += 1
            continue

        # 6. Remove questions with very short remaining text (<10 chars)
        if len(text.strip()) < 10:
            stats["removed_merged"] += 1
            continue

        # 7. Clean non-breaking spaces
        if "\xa0" in text:
            text = text.replace("\xa0", " ")
            stats["cleaned_nbsp"] += 1
        cleaned_opts = []
        for o in opts:
            o_str = str(o)
            if "\xa0" in o_str:
                o_str = o_str.replace("\xa0", " ")
            cleaned_opts.append(o_str)

        # 8. Verify answer resolves correctly
        answer_value = resolve_answer(q.get("answer", ""), cleaned_opts)
        if not answer_in_options(answer_value, cleaned_opts):
            # For questions with images, letter answers are OK (the image IS the option)
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
        "removed_unknown_answer": 0,
        "removed_answer_mismatch": 0,
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
            stats["removed_unknown_answer"] += 1
            continue

        # 2. Remove if no options
        if not opts or len(opts) < 2:
            stats["removed_answer_mismatch"] += 1
            continue

        # 3. Resolve answer and check it's in options
        answer_value = resolve_answer(answer_raw, opts)
        if not answer_in_options(answer_value, opts):
            stats["removed_answer_mismatch"] += 1
            continue

        q_out = dict(q)
        text = q_out.get("text", "")

        # 4. Strip page markers from text
        text_clean = re.sub(
            r"\s*Page\s+\d+\s*Please go on to the next page\s*>{2,}", "", text
        )
        text_clean = re.sub(r"\s*>{3,}.*$", "", text_clean)
        if text_clean != text:
            text = text_clean
            stats["cleaned_page_text"] += 1

        # 5. Clean non-breaking spaces
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
        "removed_unknown_answer": 0,
        "removed_broken_options": 0,
        "cleaned_nbsp": 0,
        "kept": 0,
    }

    result = []
    for q in data:
        opts = q.get("options", [])
        answer_raw = q.get("answer", "")

        # 1. Remove Unknown answers
        if answer_raw == "Unknown":
            stats["removed_unknown_answer"] += 1
            continue

        # 2. Remove broken GL extraction: options are just "B C D" or "B C D E"
        #    These are line-by-line comprehension/cloze extractions that don't form valid MCQs
        if opts and all(
            re.match(r"^[A-E](\s+[A-E])*$", str(o).strip()) for o in opts
        ):
            stats["removed_broken_options"] += 1
            continue

        # 3. Remove if < 3 real options
        if len(opts) < 3:
            stats["removed_broken_options"] += 1
            continue

        # 4. Clean non-breaking spaces
        q_out = dict(q)
        text = q_out.get("text", "")
        if "\xa0" in text:
            q_out["text"] = text.replace("\xa0", " ")
            stats["cleaned_nbsp"] += 1

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
        # Check image files exist
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

        # NVR questions with no question_image but with option images are valid
        # (odd-one-out type where you pick the different option image)
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

        # 1. Answer value in options (skip NVR which uses letter labels)
        if subj != "non_verbal_reasoning":
            if answer_val and opts:
                opt_strs = [str(o).strip() for o in opts]
                opt_lower = [o.lower() for o in opt_strs]
                ans = str(answer_val).strip()

                # First try direct match (handles answers containing commas)
                if ans in opt_strs or ans.lower() in opt_lower:
                    pass  # OK
                else:
                    # Try multi-answer: each comma-separated part in options
                    ans_parts = [p.strip() for p in ans.split(", ")]
                    if not all(
                        p in opt_strs or p.lower() in opt_lower for p in ans_parts
                    ):
                        issues.append(
                            f"[{i}] {subj}: answer {ans!r} not in options {opt_strs[:5]}"
                        )

        # 2. No newlines in options
        for j, o in enumerate(opts):
            if "\n" in str(o):
                issues.append(f"[{i}] {subj}: option {j} has newline: {repr(str(o)[:50])}")

        # 3. No page markers in text
        if re.search(r"Page\s+\d+\s*Please go on", text):
            issues.append(f"[{i}] {subj}: page marker in text")

        # 3b. No garbled fraction rendering in text
        if re.search(r"(?:\n.){4,}", text):
            issues.append(f"[{i}] {subj}: garbled fraction text")

        # 3c. No trailing "E <word>" artifact in question text
        if re.search(r"\?\s+E\s+\w+\s*$", text):
            issues.append(f"[{i}] {subj}: trailing E artifact in text")

        # 4. Text length (skip NVR)
        if subj != "non_verbal_reasoning" and len(text.strip()) < 10:
            issues.append(f"[{i}] {subj}: text too short ({len(text.strip())} chars)")

        # 5. NVR must have image_url or option_images
        if subj == "non_verbal_reasoning":
            has_img = content.get("image_url") or content.get("option_images")
            if not has_img:
                issues.append(f"[{i}] NVR: no images at all")

        # 6. Options count
        if len(opts) < 2:
            issues.append(f"[{i}] {subj}: only {len(opts)} option(s)")

        # 7. Maths: no letter-only options without images
        if subj == "maths" and not content.get("image_url"):
            if opts and all(re.match(r"^[A-E]$", str(o).strip()) for o in opts):
                issues.append(f"[{i}] maths: letter-only options with no image")

    return issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print("=" * 60)
    print("Question Content Audit and Fix")
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

    # Import and run the build script
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
    print(f"  Metadata after: {total_after}")
    print(f"  Removed: {total_before - total_after}")
    print(f"  Dump questions: {len(dump)}")

    return len(issues)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(1 if exit_code > 0 else 0)
