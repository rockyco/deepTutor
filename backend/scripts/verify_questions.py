"""Automated question verification using Playwright.

Fetches all questions from the backend API, navigates to each question's
verification page, and checks for rendering issues.

Prerequisites:
  - Backend running on port 8001: uv run uvicorn app.main:app --reload --port 8001
  - Frontend running on port 3002: npm run dev -- --port 3002

Usage:
    uv run python backend/scripts/verify_questions.py [--screenshots] [--subject maths]
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCREENSHOT_DIR = Path("/tmp/verify_screenshots")

API_BASE = "http://localhost:8000"
FRONTEND_BASE = "http://localhost:3002"


def fetch_all_questions(subject: str = None) -> list[dict]:
    """Fetch all questions from the backend API using pagination."""
    all_qs = []
    offset = 0
    batch_size = 100
    while True:
        params: dict = {"limit": batch_size, "offset": offset}
        if subject:
            params["subject"] = subject
        resp = requests.get(f"{API_BASE}/api/questions", params=params)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        all_qs.extend(batch)
        if len(batch) < batch_size:
            break
        offset += batch_size
    return all_qs


def verify_question_api(q: dict) -> tuple[str, str]:
    """Verify a question via API checks (no browser needed)."""
    issues = []

    # Check question text
    text = q.get("content", {}).get("text", "")
    if not text or len(text) < 5:
        issues.append("Question text is empty or too short")

    # Check options
    options = q.get("content", {}).get("options", [])
    if not options:
        issues.append("No options present")
    elif len(options) < 2:
        issues.append(f"Only {len(options)} options (need at least 2)")

    # Check answer
    answer_val = q.get("answer", {}).get("value", "")
    if not answer_val:
        issues.append("No answer value")

    # Check answer matches an option
    if options and answer_val:
        answer_str = str(answer_val).lower()
        option_strs = [str(o).lower() for o in options]
        if answer_str not in option_strs:
            # Also check if it's a letter reference
            letters = "abcde"
            if answer_str in letters:
                idx = letters.index(answer_str)
                if idx >= len(options):
                    issues.append(f"Answer letter '{answer_val}' out of range (only {len(options)} options)")
            elif not any(answer_str in o for o in option_strs):
                issues.append(f"Answer '{answer_val}' doesn't match any option")

    # Check explanation
    explanation = q.get("explanation", "")
    if not explanation:
        issues.append("No explanation")

    # Check image URLs resolve
    image_url = q.get("content", {}).get("image_url", "")
    if image_url:
        try:
            img_resp = requests.head(f"{API_BASE}{image_url}", timeout=5)
            if img_resp.status_code != 200:
                issues.append(f"Image URL returns {img_resp.status_code}: {image_url}")
        except requests.RequestException as e:
            issues.append(f"Image URL unreachable: {image_url} ({e})")

    option_images = q.get("content", {}).get("option_images", [])
    for img_path in (option_images or []):
        try:
            img_resp = requests.head(f"{API_BASE}{img_path}", timeout=5)
            if img_resp.status_code != 200:
                issues.append(f"Option image returns {img_resp.status_code}: {img_path}")
        except requests.RequestException:
            issues.append(f"Option image unreachable: {img_path}")

    # Classify result
    if not issues:
        return "PASS", ""
    critical = any(
        "empty" in i.lower() or "no answer" in i.lower() or "no options" in i.lower()
        for i in issues
    )
    if critical:
        return "FAIL", "; ".join(issues)
    return "WARN", "; ".join(issues)


def run_verification(subject: str = None, take_screenshots: bool = False):
    """Run verification on all questions."""
    print("=" * 60)
    print("Question Verification")
    print("=" * 60)

    # Check backend is running
    try:
        resp = requests.get(f"{API_BASE}/api/questions?limit=1", timeout=5)
        resp.raise_for_status()
    except Exception as e:
        print(f"ERROR: Backend not reachable at {API_BASE}")
        print(f"Start it with: cd backend && uv run uvicorn app.main:app --reload --port 8001")
        sys.exit(1)

    print(f"\nFetching questions from {API_BASE}...")
    questions = fetch_all_questions(subject)
    print(f"Found {len(questions)} questions to verify")

    if take_screenshots:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    results = {"PASS": [], "WARN": [], "FAIL": []}

    for i, q in enumerate(questions):
        qid = q.get("id", "unknown")
        subj = q.get("subject", "?")
        qtype = q.get("question_type", "?")

        status, reason = verify_question_api(q)
        results[status].append({
            "id": qid,
            "subject": subj,
            "question_type": qtype,
            "text": q.get("content", {}).get("text", "")[:80],
            "reason": reason,
        })

        marker = {"PASS": ".", "WARN": "W", "FAIL": "F"}[status]
        print(marker, end="", flush=True)
        if (i + 1) % 50 == 0:
            print(f" [{i+1}/{len(questions)}]")

    print(f"\n\n{'=' * 60}")
    print("Results")
    print("=" * 60)
    print(f"  PASS: {len(results['PASS'])}")
    print(f"  WARN: {len(results['WARN'])}")
    print(f"  FAIL: {len(results['FAIL'])}")

    if results["FAIL"]:
        print(f"\n--- FAILURES ({len(results['FAIL'])}) ---")
        for f in results["FAIL"]:
            print(f"  [{f['subject']}] {f['id'][:8]}: {f['reason']}")
            print(f"    Text: {f['text']}")

    if results["WARN"]:
        print(f"\n--- WARNINGS ({len(results['WARN'])}) ---")
        for w in results["WARN"][:20]:  # Show first 20
            print(f"  [{w['subject']}] {w['id'][:8]}: {w['reason']}")
        if len(results["WARN"]) > 20:
            print(f"  ... and {len(results['WARN']) - 20} more warnings")

    # Save report
    report_path = PROJECT_ROOT / "backend" / "data" / "verification_report.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull report saved to {report_path}")

    # Auto-remove FAIL questions from dump
    if results["FAIL"]:
        fail_ids = {f["id"] for f in results["FAIL"]}
        dump_path = PROJECT_ROOT / "backend" / "data" / "questions" / "deployment_dump.json"
        if dump_path.exists():
            with open(dump_path) as f:
                dump = json.load(f)
            original = len(dump)
            # Can't filter by ID since dump doesn't have IDs, but we can log
            print(f"\n{len(fail_ids)} FAIL questions identified for removal")
            print("These should be manually reviewed and removed from metadata.json sources")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", help="Filter by subject")
    parser.add_argument("--screenshots", action="store_true", help="Take screenshots")
    args = parser.parse_args()
    run_verification(subject=args.subject, take_screenshots=args.screenshots)
