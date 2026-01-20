#!/usr/bin/env python3
"""Import questions from open educational datasets.

Sources:
- GSM8K: Grade School Math 8K (OpenAI) - math word problems
- ARC: AI2 Reasoning Challenge - science reasoning questions

Usage:
    uv run python scripts/import_datasets.py --source gsm8k --limit 500
    uv run python scripts/import_datasets.py --source arc --limit 500
    uv run python scripts/import_datasets.py --all --limit 200
"""

import argparse
import json
import random
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

try:
    from datasets import load_dataset
except ImportError:
    print("ERROR: 'datasets' package not installed.")
    print("Install with: uv pip install datasets")
    exit(1)


def get_db_connection():
    """Get database connection."""
    db_path = Path(__file__).parent.parent / "data" / "tutor.db"
    return sqlite3.connect(db_path)


def extract_answer_from_solution(solution: str) -> str:
    """Extract the numerical answer from a GSM8K solution."""
    # GSM8K answers are typically at the end after ####
    if "####" in solution:
        answer = solution.split("####")[-1].strip()
        return answer

    # Try to find the last number in the solution
    numbers = re.findall(r'-?\d+(?:,\d{3})*(?:\.\d+)?', solution)
    if numbers:
        return numbers[-1].replace(",", "")

    return ""


def classify_math_type(question: str, answer: str) -> str:
    """Classify the math question type based on content."""
    q_lower = question.lower()

    # Check for specific patterns
    if any(w in q_lower for w in ["fraction", "half", "quarter", "third"]):
        return "fractions"
    if any(w in q_lower for w in ["percent", "%"]):
        return "percentages"
    if any(w in q_lower for w in ["ratio", "proportion"]):
        return "ratio"
    if any(w in q_lower for w in ["area", "perimeter", "square", "rectangle", "triangle", "circle"]):
        return "geometry"
    if any(w in q_lower for w in ["hour", "minute", "second", "day", "week", "time"]):
        return "measurement"
    if any(w in q_lower for w in ["graph", "table", "chart", "average", "mean"]):
        return "data_handling"
    if "." in answer and answer.replace(".", "").replace("-", "").isdigit():
        return "decimals"

    return "word_problems"


def estimate_difficulty(question: str, solution: str) -> int:
    """Estimate question difficulty (1-5)."""
    # Count steps in solution
    lines = [l for l in solution.split('\n') if l.strip() and not l.startswith('#')]
    step_count = len(lines)

    # Count operations
    operations = len(re.findall(r'[+\-*/=]', solution))

    # Simple heuristics
    if step_count <= 2 and operations <= 3:
        return 1
    elif step_count <= 3 and operations <= 5:
        return 2
    elif step_count <= 5 and operations <= 8:
        return 3
    elif step_count <= 7:
        return 4
    else:
        return 5


def import_gsm8k(limit: int = 500, dry_run: bool = False) -> list[dict]:
    """Import questions from GSM8K dataset."""
    print("Loading GSM8K dataset...")
    dataset = load_dataset("openai/gsm8k", "main", split="train")

    print(f"Dataset has {len(dataset)} questions")

    # Shuffle and limit
    indices = list(range(len(dataset)))
    random.shuffle(indices)
    indices = indices[:limit]

    questions = []
    for idx in indices:
        item = dataset[idx]
        question_text = item["question"]
        solution = item["answer"]

        # Extract the numerical answer
        answer = extract_answer_from_solution(solution)
        if not answer:
            continue

        # Clean up solution for explanation
        explanation = solution.replace("####", "\nFinal Answer:").strip()

        # Classify question type
        qtype = classify_math_type(question_text, answer)

        # Estimate difficulty
        difficulty = estimate_difficulty(question_text, solution)

        questions.append({
            "id": str(uuid.uuid4()),
            "subject": "maths",
            "question_type": qtype,
            "format": "fill_in_blank",
            "difficulty": difficulty,
            "content": {
                "text": question_text,
                "passage": None,
                "options": None,
                "image_url": None,
                "images": None,
                "items": None,
                "pairs": None,
                "context": None,
            },
            "answer": {
                "value": answer,
                "accept_variations": None,
                "case_sensitive": False,
                "order_matters": True,
            },
            "explanation": explanation,
            "hints": [
                {"level": 1, "text": "Read the problem carefully and identify what you need to find.", "penalty": 0.1},
                {"level": 2, "text": "Break the problem into smaller steps.", "penalty": 0.2},
            ],
            "tags": ["word_problems", "gsm8k"],
            "source": "gsm8k",
            "created_at": datetime.utcnow().isoformat(),
        })

    print(f"Processed {len(questions)} GSM8K questions")
    return questions


def import_arc(limit: int = 500, dry_run: bool = False) -> list[dict]:
    """Import questions from ARC dataset."""
    print("Loading ARC dataset...")

    # Load both easy and challenge sets
    try:
        easy = load_dataset("allenai/ai2_arc", "ARC-Easy", split="train")
        challenge = load_dataset("allenai/ai2_arc", "ARC-Challenge", split="train")
    except Exception as e:
        print(f"Error loading ARC dataset: {e}")
        return []

    print(f"ARC Easy: {len(easy)} questions, Challenge: {len(challenge)} questions")

    # Combine and shuffle
    all_items = list(easy) + list(challenge)
    random.shuffle(all_items)

    questions = []
    for item in all_items[:limit]:
        question_text = item["question"]
        choices = item["choices"]
        answer_key = item["answerKey"]

        # Get options and correct answer
        options = choices["text"]
        labels = choices["label"]

        # Find correct answer
        try:
            answer_idx = labels.index(answer_key)
            correct_answer = options[answer_idx]
        except (ValueError, IndexError):
            continue

        # Skip questions with too few options
        if len(options) < 2:
            continue

        # Determine difficulty based on source
        difficulty = 3 if "Challenge" in str(item.get("source", "")) else 2

        # Map to our question type (science reasoning -> verbal reasoning logic problems)
        qtype = "vr_logic_problems"

        questions.append({
            "id": str(uuid.uuid4()),
            "subject": "verbal_reasoning",
            "question_type": qtype,
            "format": "multiple_choice",
            "difficulty": difficulty,
            "content": {
                "text": question_text,
                "passage": None,
                "options": options,
                "image_url": None,
                "images": None,
                "items": None,
                "pairs": None,
                "context": None,
            },
            "answer": {
                "value": correct_answer,
                "accept_variations": None,
                "case_sensitive": False,
                "order_matters": True,
            },
            "explanation": f"The correct answer is: {correct_answer}",
            "hints": [
                {"level": 1, "text": "Think about what you know about this topic.", "penalty": 0.1},
                {"level": 2, "text": "Eliminate answers that don't make sense.", "penalty": 0.2},
            ],
            "tags": ["science", "reasoning", "arc"],
            "source": "arc",
            "created_at": datetime.utcnow().isoformat(),
        })

    print(f"Processed {len(questions)} ARC questions")
    return questions


def save_to_database(questions: list[dict], dry_run: bool = False):
    """Save questions to database."""
    if dry_run:
        print(f"\n[DRY RUN] Would save {len(questions)} questions")
        # Show sample
        for q in questions[:3]:
            print(f"\n  Subject: {q['subject']}, Type: {q['question_type']}")
            print(f"  Q: {q['content']['text'][:80]}...")
            print(f"  A: {q['answer']['value']}")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    inserted = 0
    for q in questions:
        try:
            cursor.execute(
                """
                INSERT INTO questions
                (id, subject, question_type, format, difficulty, content, answer,
                 explanation, hints, tags, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    q["id"],
                    q["subject"],
                    q["question_type"],
                    q["format"],
                    q["difficulty"],
                    json.dumps(q["content"]),
                    json.dumps(q["answer"]),
                    q["explanation"],
                    json.dumps(q["hints"]),
                    json.dumps(q["tags"]),
                    q["source"],
                    q["created_at"],
                )
            )
            inserted += 1
        except sqlite3.IntegrityError:
            pass  # Skip duplicates

    conn.commit()
    conn.close()

    print(f"\nSaved {inserted} questions to database")


def main():
    parser = argparse.ArgumentParser(description="Import questions from open datasets")
    parser.add_argument("--source", choices=["gsm8k", "arc"], help="Dataset to import")
    parser.add_argument("--all", action="store_true", help="Import from all sources")
    parser.add_argument("--limit", type=int, default=500, help="Max questions per source")
    parser.add_argument("--dry-run", action="store_true", help="Don't save to database")

    args = parser.parse_args()

    all_questions = []

    if args.all or args.source == "gsm8k":
        questions = import_gsm8k(args.limit, args.dry_run)
        all_questions.extend(questions)

    if args.all or args.source == "arc":
        questions = import_arc(args.limit, args.dry_run)
        all_questions.extend(questions)

    if not args.source and not args.all:
        print("ERROR: Specify --source or --all")
        return

    print(f"\n{'='*50}")
    print(f"Total questions: {len(all_questions)}")
    print(f"{'='*50}")

    if all_questions:
        save_to_database(all_questions, args.dry_run)

        # Show final counts
        if not args.dry_run:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT subject, COUNT(*) FROM questions GROUP BY subject")
            print("\nQuestions by subject:")
            for row in cursor.fetchall():
                print(f"  {row[0]}: {row[1]}")
            conn.close()


if __name__ == "__main__":
    main()
