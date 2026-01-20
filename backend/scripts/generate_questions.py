#!/usr/bin/env python3
"""Generate high-quality 11+ questions using Claude AI.

Usage:
    uv run python scripts/generate_questions.py --subject maths --count 50
    uv run python scripts/generate_questions.py --all --count 20
    uv run python scripts/generate_questions.py --dry-run
"""

import argparse
import json
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import anthropic

# Question type definitions for each subject
QUESTION_TYPES = {
    "english": [
        ("comprehension", "Reading comprehension with passage and questions"),
        ("grammar", "Grammar rules: tenses, punctuation, parts of speech"),
        ("spelling", "Spelling patterns, commonly misspelled words"),
        ("vocabulary", "Word meanings, synonyms, antonyms"),
        ("sentence_completion", "Complete sentences with appropriate words"),
    ],
    "maths": [
        ("number_operations", "Addition, subtraction, multiplication, division"),
        ("fractions", "Operations with fractions, simplification, comparison"),
        ("decimals", "Decimal operations, conversion, place value"),
        ("percentages", "Finding percentages, percentage increase/decrease"),
        ("geometry", "Shapes, angles, area, perimeter, properties"),
        ("measurement", "Time, length, weight, capacity conversions"),
        ("data_handling", "Interpreting tables, charts, graphs, averages"),
        ("word_problems", "Multi-step real-world mathematical problems"),
        ("algebra", "Simple equations, patterns, number relationships"),
        ("ratio", "Ratios, proportions, sharing quantities"),
    ],
    "verbal_reasoning": [
        ("vr_synonyms", "Find words with similar meanings"),
        ("vr_odd_ones_out", "Identify the word that doesn't belong"),
        ("vr_hidden_word", "Find a word hidden between other words"),
        ("vr_missing_word", "Complete sentences with missing words"),
        ("vr_number_series", "Continue number sequences and patterns"),
        ("vr_letter_series", "Continue letter sequences and patterns"),
        ("vr_alphabet_code", "Decode words using letter shifts"),
        ("vr_word_pairs", "Find word relationships and analogies"),
        ("vr_anagrams", "Rearrange letters to form words"),
        ("vr_compound_words", "Combine words to make compound words"),
        ("vr_logic_problems", "Solve logical reasoning problems"),
    ],
    "non_verbal_reasoning": [
        ("nvr_sequences", "Continue shape/pattern sequences"),
        ("nvr_odd_one_out", "Identify the shape that doesn't belong"),
        ("nvr_analogies", "A is to B as C is to ?"),
        ("nvr_rotation", "Identify rotated shapes"),
        ("nvr_reflection", "Identify reflected/mirrored shapes"),
    ],
}


def get_generation_prompt(subject: str, question_type: str, type_description: str, count: int) -> str:
    """Build the prompt for generating questions."""

    return f"""Generate {count} high-quality 11+ exam questions for UK students aged 10-11.

Subject: {subject.replace('_', ' ').title()}
Question Type: {question_type.replace('_', ' ').replace('vr ', 'verbal reasoning: ').replace('nvr ', 'non-verbal reasoning: ')}
Description: {type_description}

Requirements:
1. Age-appropriate difficulty for 11+ exams (challenging but fair)
2. Clear, unambiguous questions
3. For multiple choice: exactly 4 options, only ONE correct answer
4. Correct answers must be accurate and verifiable
5. Explanations should teach the concept, not just state the answer
6. Vary difficulty (mix of easy, medium, hard questions)

Output JSON array with this exact structure:
[
  {{
    "text": "The question text",
    "passage": "Optional reading passage for comprehension questions, null otherwise",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": "The exact text of the correct option",
    "explanation": "Step-by-step explanation of why this is correct",
    "difficulty": 1-5 (1=easy, 3=medium, 5=hard),
    "hints": [
      {{"level": 1, "text": "First hint - gentle nudge"}},
      {{"level": 2, "text": "Second hint - more specific"}}
    ]
  }}
]

For fill-in-the-blank questions (like algebra, letter series), omit the "options" field.

Important:
- Ensure mathematical calculations are CORRECT
- For vocabulary: use words appropriate for 10-11 year olds
- For verbal reasoning: follow standard 11+ exam patterns
- For non-verbal reasoning: describe shapes/patterns clearly (no actual images)

Generate exactly {count} questions. Output ONLY the JSON array, no other text."""


def generate_questions_for_type(
    client: anthropic.Anthropic,
    subject: str,
    question_type: str,
    type_description: str,
    count: int,
) -> list[dict]:
    """Generate questions for a specific type using Claude."""

    prompt = get_generation_prompt(subject, question_type, type_description, count)

    print(f"  Generating {count} {question_type} questions...")

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    response_text = message.content[0].text

    # Parse JSON from response
    try:
        # Handle potential markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        questions = json.loads(response_text.strip())

        # Validate and transform to database format
        validated = []
        for q in questions:
            validated.append({
                "id": str(uuid.uuid4()),
                "subject": subject,
                "question_type": question_type,
                "format": "multiple_choice" if q.get("options") else "fill_in_blank",
                "difficulty": q.get("difficulty", 3),
                "content": {
                    "text": q["text"],
                    "passage": q.get("passage"),
                    "options": q.get("options"),
                    "image_url": None,
                    "images": None,
                    "items": None,
                    "pairs": None,
                    "context": None,
                },
                "answer": {
                    "value": q["correct_answer"],
                    "accept_variations": None,
                    "case_sensitive": False,
                    "order_matters": True,
                },
                "explanation": q.get("explanation", ""),
                "hints": q.get("hints", []),
                "tags": [question_type.replace("vr_", "").replace("nvr_", "")],
                "source": "ai_generated",
                "created_at": datetime.utcnow().isoformat(),
            })

        print(f"    Generated {len(validated)} valid questions")
        return validated

    except json.JSONDecodeError as e:
        print(f"    ERROR: Failed to parse response: {e}")
        print(f"    Response preview: {response_text[:200]}...")
        return []


def validate_question(q: dict) -> tuple[bool, str]:
    """Validate a generated question."""
    content = q.get("content", {})
    answer = q.get("answer", {})

    # Check required fields
    if not content.get("text"):
        return False, "Missing question text"

    if not answer.get("value"):
        return False, "Missing answer"

    # For multiple choice, validate answer is in options
    options = content.get("options")
    if options:
        if len(options) < 2:
            return False, "Too few options"
        if answer["value"] not in options:
            return False, f"Answer '{answer['value']}' not in options"

    return True, ""


def save_to_database(questions: list[dict], db_path: Path, dry_run: bool = False):
    """Save questions to the SQLite database."""

    if dry_run:
        print(f"\n[DRY RUN] Would save {len(questions)} questions")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    inserted = 0
    for q in questions:
        valid, error = validate_question(q)
        if not valid:
            print(f"  Skipping invalid question: {error}")
            continue

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

    conn.commit()
    conn.close()

    print(f"\nSaved {inserted} questions to database")


def export_to_json(questions: list[dict], output_dir: Path):
    """Export questions to JSON files by subject."""

    by_subject = {}
    for q in questions:
        subject = q["subject"]
        if subject not in by_subject:
            by_subject[subject] = []
        by_subject[subject].append(q)

    for subject, qs in by_subject.items():
        output_file = output_dir / f"{subject}_generated.json"
        with open(output_file, "w") as f:
            json.dump(qs, f, indent=2)
        print(f"Exported {len(qs)} questions to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Generate 11+ questions using AI")
    parser.add_argument("--subject", choices=list(QUESTION_TYPES.keys()), help="Subject to generate")
    parser.add_argument("--type", help="Specific question type (e.g., vr_synonyms)")
    parser.add_argument("--count", type=int, default=10, help="Questions per type")
    parser.add_argument("--all", action="store_true", help="Generate for all subjects/types")
    parser.add_argument("--dry-run", action="store_true", help="Don't save to database")
    parser.add_argument("--export-json", action="store_true", help="Also export to JSON files")

    args = parser.parse_args()

    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        print("Set it with: export ANTHROPIC_API_KEY=your-key")
        return

    client = anthropic.Anthropic(api_key=api_key)
    db_path = Path(__file__).parent.parent / "data" / "tutor.db"

    all_questions = []

    if args.all:
        # Generate for all subjects and types
        for subject, types in QUESTION_TYPES.items():
            print(f"\n{'='*50}")
            print(f"Subject: {subject}")
            print(f"{'='*50}")

            for qtype, desc in types:
                questions = generate_questions_for_type(
                    client, subject, qtype, desc, args.count
                )
                all_questions.extend(questions)

    elif args.subject:
        # Generate for specific subject
        types = QUESTION_TYPES.get(args.subject, [])

        if args.type:
            # Specific type only
            types = [(t, d) for t, d in types if t == args.type]
            if not types:
                print(f"ERROR: Unknown question type '{args.type}' for {args.subject}")
                return

        print(f"\n{'='*50}")
        print(f"Subject: {args.subject}")
        print(f"{'='*50}")

        for qtype, desc in types:
            questions = generate_questions_for_type(
                client, args.subject, qtype, desc, args.count
            )
            all_questions.extend(questions)

    else:
        print("ERROR: Specify --subject or --all")
        return

    print(f"\n{'='*50}")
    print(f"Total questions generated: {len(all_questions)}")
    print(f"{'='*50}")

    if all_questions:
        save_to_database(all_questions, db_path, dry_run=args.dry_run)

        if args.export_json:
            export_to_json(all_questions, db_path.parent / "questions")


if __name__ == "__main__":
    main()
