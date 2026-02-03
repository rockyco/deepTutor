"""Generate lesson content JSON using Gemini API.

Reads existing prompt templates from backend/scripts/prompts/ and uses Gemini
to produce structured lesson JSON for each question type. The output JSON files
are saved to backend/data/lessons/.

Usage:
    cd backend && uv run python scripts/generate_lessons.py [--subject maths] [--type fractions]

The generated JSON should be reviewed before committing.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LESSONS_DIR = PROJECT_ROOT / "data" / "lessons"
PROMPTS_DIR = PROJECT_ROOT / "scripts" / "prompts"

SUBJECT_CONFIG = {
    "english": {
        "file": "english_lessons.json",
        "types": [
            "comprehension", "grammar", "spelling", "vocabulary",
            "sentence_completion", "punctuation",
        ],
    },
    "maths": {
        "file": "maths_lessons.json",
        "types": [
            "number_operations", "fractions", "decimals", "percentages",
            "geometry", "measurement", "data_handling", "word_problems",
            "algebra", "ratio",
        ],
    },
    "verbal_reasoning": {
        "file": "verbal_reasoning_lessons.json",
        "types": [
            "vr_synonyms", "vr_odd_ones_out", "vr_hidden_word", "vr_missing_word",
            "vr_number_series", "vr_letter_series", "vr_number_connections",
            "vr_word_pairs", "vr_multiple_meaning", "vr_letter_relationships",
            "vr_number_codes", "vr_compound_words", "vr_word_shuffling",
            "vr_anagrams", "vr_logic_problems", "vr_explore_facts",
            "vr_solve_riddle", "vr_rhyming_synonyms", "vr_shuffled_sentences",
            "vr_insert_letter", "vr_alphabet_code",
        ],
    },
    "non_verbal_reasoning": {
        "file": "non_verbal_reasoning_lessons.json",
        "types": [
            "nvr_sequences", "nvr_odd_one_out", "nvr_analogies", "nvr_matrices",
            "nvr_rotation", "nvr_reflection", "nvr_spatial_3d", "nvr_codes",
            "nvr_visual",
        ],
    },
}

LESSON_SCHEMA = """{
  "questionType": "<type>",
  "title": "<human readable title>",
  "subtitle": "<one line description>",
  "difficulty": "foundation|intermediate",
  "color": "<tailwind color name>",
  "sections": [
    {
      "type": "intro",
      "heading": "What is this question type?",
      "body": "<HTML string explaining the question type for Year 5 students>",
      "visual": { "type": "mermaid", "code": "<mermaid flowchart>" }
    },
    {
      "type": "strategy",
      "heading": "Strategy: Steps to Solve",
      "steps": [
        { "label": "<step name>", "detail": "<explanation>",
          "icon": "eye|link|check|brain|search|pencil|puzzle|lightbulb" }
      ]
    },
    {
      "type": "worked_example",
      "heading": "Worked Example",
      "question": { "text": "<GL format question>", "options": ["A", "B", "C", "D", "E"] },
      "walkthrough": [
        { "step": 1, "text": "<step explanation>",
          "highlight": "group1|group2|answer|verify|operation" }
      ],
      "answer": "<correct option text>"
    },
    {
      "type": "tips",
      "heading": "Common Traps",
      "items": [
        { "trap": "<common mistake>", "fix": "<how to avoid>" }
      ]
    },
    {
      "type": "practice",
      "heading": "Try It Yourself",
      "questions": []
    },
    {
      "type": "assessment",
      "heading": "Quick Check",
      "questions": []
    }
  ]
}"""


def build_prompt(subject: str, qtype: str) -> str:
    """Build a Gemini prompt for generating a lesson."""
    # Try to load existing prompt template for context
    context = ""
    prompt_file = PROMPTS_DIR / f"{subject}.py"
    if prompt_file.exists():
        context = f"\nReference prompt file content available at: {prompt_file}\n"

    return f"""Generate a lesson JSON object for the 11+ GL Assessment question type "{qtype}"
in subject "{subject}". This is for Year 5 students (age 10-11) in the UK preparing for
selective school entrance exams.

The lesson must follow this exact JSON schema:
{LESSON_SCHEMA}

Requirements:
- The intro body should be 2-3 paragraphs of HTML explaining the question type clearly
- The mermaid diagram should illustrate the solving strategy or concept structure
- Strategy should have 3-4 concrete steps
- The worked example must use authentic GL Assessment question format with 5 options
- The worked example walkthrough should be 3-5 steps
- Tips should cover 2-3 common mistakes Year 5 students make
- Practice and assessment questions arrays should be empty []
- The answer must be mathematically/linguistically correct

{context}

Return ONLY the JSON object, no markdown wrapping."""


def generate_with_gemini(prompt: str) -> dict:
    """Call Gemini API to generate lesson content."""
    try:
        import google.generativeai as genai
    except ImportError:
        print("ERROR: google-generativeai not installed. Run: uv pip install google-generativeai")
        sys.exit(1)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set in environment")
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.7,
        ),
    )

    return json.loads(response.text)


def main():
    parser = argparse.ArgumentParser(description="Generate lesson content using Gemini")
    parser.add_argument("--subject", help="Generate for specific subject only")
    parser.add_argument("--type", help="Generate for specific question type only")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without calling API")
    args = parser.parse_args()

    LESSONS_DIR.mkdir(parents=True, exist_ok=True)

    subjects = [args.subject] if args.subject else list(SUBJECT_CONFIG.keys())

    for subject in subjects:
        config = SUBJECT_CONFIG.get(subject)
        if not config:
            print(f"Unknown subject: {subject}")
            continue

        output_file = LESSONS_DIR / config["file"]
        existing = []
        if output_file.exists():
            with open(output_file) as f:
                existing = json.load(f)
            existing_types = {item["questionType"] for item in existing}
        else:
            existing_types = set()

        types = [args.type] if args.type else config["types"]

        for qtype in types:
            if qtype in existing_types and not args.type:
                print(f"  {subject}/{qtype}: already exists, skipping")
                continue

            print(f"  Generating {subject}/{qtype}...")
            prompt = build_prompt(subject, qtype)

            if args.dry_run:
                print(f"    [DRY RUN] Prompt length: {len(prompt)} chars")
                continue

            try:
                lesson = generate_with_gemini(prompt)
                # Replace if exists, append if new
                existing = [item for item in existing if item["questionType"] != qtype]
                existing.append(lesson)
                print(f"    Generated: {lesson.get('title', 'untitled')}")
            except Exception as e:
                print(f"    ERROR: {e}")
                continue

        if not args.dry_run:
            with open(output_file, "w") as f:
                json.dump(existing, f, indent=2)
            print(f"  Saved {len(existing)} lessons to {output_file}")

    print("\nDone. Review the generated JSON before committing.")


if __name__ == "__main__":
    main()
