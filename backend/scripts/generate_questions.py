"""Generate 11+ GL Assessment questions using Gemini.

Generates questions by subject/type in batches, targeting ~540 total
for 3 complete mock exams (180 questions each).
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google import genai
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-2.0-flash"
DELAY_BETWEEN_BATCHES = 12  # seconds between API calls

# Target distribution: 3 exams x 2 papers x sections
TARGETS = {
    # English comprehension: 12 per paper x 2 papers x 3 exams = 72
    ("english", "comprehension"): 72,
    # English vocabulary: 8 per paper x 2 papers x 3 exams = 48
    ("english", "vocabulary"): 48,
    # Maths: 30 per paper x 2 papers x 3 exams = 180
    ("maths", "number_operations"): 30,
    ("maths", "fractions"): 25,
    ("maths", "geometry"): 20,
    ("maths", "measurement"): 20,
    ("maths", "word_problems"): 25,
    ("maths", "data_handling"): 20,
    ("maths", "algebra"): 20,
    ("maths", "ratio"): 20,
    # NVR: 20 per paper x 2 papers x 3 exams = 120
    ("non_verbal_reasoning", "nvr_sequences"): 20,
    ("non_verbal_reasoning", "nvr_odd_one_out"): 20,
    ("non_verbal_reasoning", "nvr_analogies"): 20,
    ("non_verbal_reasoning", "nvr_codes"): 20,
    ("non_verbal_reasoning", "nvr_matrices"): 20,
    ("non_verbal_reasoning", "nvr_rotation"): 20,
    # VR: 20 per paper x 2 papers x 3 exams = 120
    ("verbal_reasoning", "vr_synonyms"): 10,
    ("verbal_reasoning", "vr_odd_ones_out"): 10,
    ("verbal_reasoning", "vr_hidden_word"): 10,
    ("verbal_reasoning", "vr_missing_word"): 10,
    ("verbal_reasoning", "vr_number_series"): 10,
    ("verbal_reasoning", "vr_letter_series"): 10,
    ("verbal_reasoning", "vr_word_pairs"): 10,
    ("verbal_reasoning", "vr_anagrams"): 10,
    ("verbal_reasoning", "vr_compound_words"): 10,
    ("verbal_reasoning", "vr_logic_problems"): 10,
    ("verbal_reasoning", "vr_insert_letter"): 10,
    ("verbal_reasoning", "vr_alphabet_code"): 10,
}

# Prompt templates per subject/type
PROMPTS = {
    ("english", "comprehension"): """Generate {count} English comprehension questions for 11+ GL Assessment (Year 5, age 10-11).

Each question must have:
- A short reading passage (60-120 words, age-appropriate fiction or non-fiction)
- A question about the passage
- Exactly 5 answer options (A-E style), only 1 correct
- Questions should test: inference, vocabulary in context, main idea, author's purpose, detail retrieval

Return a JSON array of objects with this exact format:
[
  {{
    "subject": "english",
    "question_type": "comprehension",
    "format": "multiple_choice",
    "difficulty": 3,
    "content": {{
      "text": "Read the passage and answer the question.\n\n[Question text here]",
      "passage": "[The reading passage here]",
      "options": ["Option A", "Option B", "Option C", "Option D", "Option E"]
    }},
    "answer": {{ "value": "[Exact text of the correct option]" }},
    "explanation": "[Why this answer is correct]",
    "hints": [],
    "tags": ["comprehension"],
    "source": "LLM Generated"
  }}
]

IMPORTANT: Every answer must be factually correct. The correct answer must match one of the options exactly. Vary the position of the correct answer across questions. Generate exactly {count} questions.""",

    ("english", "vocabulary"): """Generate {count} English vocabulary questions for 11+ GL Assessment (Year 5, age 10-11).

Mix these vocabulary question types:
- Word meanings / definitions
- Synonyms (closest in meaning)
- Antonyms (most opposite in meaning)
- Word in context (which word best fits the gap)
- Odd word out (which word does not belong)

Each question must have exactly 5 answer options, only 1 correct.

Return a JSON array:
[
  {{
    "subject": "english",
    "question_type": "vocabulary",
    "format": "multiple_choice",
    "difficulty": 3,
    "content": {{
      "text": "[Question text]",
      "options": ["Option A", "Option B", "Option C", "Option D", "Option E"]
    }},
    "answer": {{ "value": "[Exact text of correct option]" }},
    "explanation": "[Why this answer is correct]",
    "hints": [],
    "tags": ["vocabulary"],
    "source": "LLM Generated"
  }}
]

IMPORTANT: Answers must be correct. Vary correct answer position. Generate exactly {count} questions.""",

    ("maths", "_default"): """Generate {count} Year 5 (age 10-11) GL Assessment maths questions of type: {qtype}.

Topic guidance for {qtype}:
- number_operations: addition, subtraction, multiplication, division, place value, ordering, rounding, factors, multiples, primes, squares, cubes
- fractions: comparing, ordering, adding, subtracting, multiplying fractions, mixed numbers, equivalent fractions, fraction of an amount
- geometry: angles, properties of 2D/3D shapes, coordinates, symmetry, perimeter, area, volume
- measurement: length, mass, capacity, time, converting units, reading scales
- word_problems: multi-step problems using any maths topic, real-world context
- data_handling: reading tables, bar charts, pie charts, line graphs, mean, median, mode
- algebra: simple equations, sequences, function machines, missing number problems
- ratio: ratio notation, simplifying ratios, sharing in a ratio, proportion, scaling

Each question must have exactly 5 options, only 1 correct. Questions should be challenging but solvable by a strong Year 5 student.

Return a JSON array:
[
  {{
    "subject": "maths",
    "question_type": "{qtype}",
    "format": "multiple_choice",
    "difficulty": 3,
    "content": {{
      "text": "[Question text - can include mathematical notation using simple text like 2/3, x^2, etc.]",
      "options": ["Option A", "Option B", "Option C", "Option D", "Option E"]
    }},
    "answer": {{ "value": "[Exact text of correct option]" }},
    "explanation": "[Step-by-step solution]",
    "hints": [],
    "tags": ["{qtype}"],
    "source": "LLM Generated"
  }}
]

IMPORTANT: Every answer must be mathematically correct. Show working in explanation. Vary correct answer position. Generate exactly {count} questions.""",

    ("non_verbal_reasoning", "_default"): """Generate {count} non-verbal reasoning questions for 11+ GL Assessment (Year 5, age 10-11).

Question type: {qtype}

Since these are text-based (no images), describe visual patterns using text notation:
- Use shape names: circle, square, triangle, pentagon, hexagon, star, arrow, cross, diamond
- Use properties: small/large, filled/empty/striped, black/white/grey, rotated 90/180/270 degrees
- Use position: top-left, center, bottom-right, inside, outside, overlapping

Type guidance for {qtype}:
- nvr_sequences: "Which comes next?" - describe a sequence of 4 shapes/patterns, ask for the 5th
- nvr_odd_one_out: "Which is the odd one out?" - 5 shapes/patterns, one doesn't follow the rule
- nvr_analogies: "A is to B as C is to ?" - shape relationship analogy
- nvr_codes: shapes have letter/number codes, work out the code for a new shape
- nvr_matrices: 3x3 grid with pattern, find the missing piece
- nvr_rotation: identify which shape is a rotation/reflection of the given shape

Each question must have exactly 5 options, only 1 correct.

Return a JSON array:
[
  {{
    "subject": "non_verbal_reasoning",
    "question_type": "{qtype}",
    "format": "multiple_choice",
    "difficulty": 3,
    "content": {{
      "text": "[Detailed text description of the visual pattern/problem]",
      "options": ["Option A", "Option B", "Option C", "Option D", "Option E"]
    }},
    "answer": {{ "value": "[Exact text of correct option]" }},
    "explanation": "[Explain the pattern/rule and why the answer is correct]",
    "hints": [],
    "tags": ["{qtype}"],
    "source": "LLM Generated"
  }}
]

IMPORTANT: Describe patterns clearly so they can be understood without images. Answers must be correct. Generate exactly {count} questions.""",

    ("verbal_reasoning", "_default"): """Generate {count} verbal reasoning questions for 11+ GL Assessment (Year 5, age 10-11).

Question type: {qtype}

Type guidance:
- vr_synonyms: "Find two words, one from each group, closest in meaning" (two groups of 3 words)
- vr_odd_ones_out: "Which word is the odd one out?" (5 words, one doesn't belong)
- vr_hidden_word: "Find a word hidden across two adjacent words in the sentence"
- vr_missing_word: "Complete the sentence by choosing the missing word"
- vr_number_series: "Find the next number in the series" (e.g., 2, 5, 8, 11, ?)
- vr_letter_series: "Find the next pair of letters" (e.g., AB, CD, EF, ?)
- vr_word_pairs: "Complete the analogy: hot is to cold as big is to ?"
- vr_anagrams: "Rearrange the letters to make a word" (scrambled word)
- vr_compound_words: "Join two words to make a compound word or new word"
- vr_logic_problems: "Use the clues to work out the answer" (short logic puzzle)
- vr_insert_letter: "Find the letter that completes both words: s_n (letter) _gg"
- vr_alphabet_code: "If A=1, B=2... what is the code for HELLO?" or letter shift codes

Each question must have exactly 5 options, only 1 correct.

Return a JSON array:
[
  {{
    "subject": "verbal_reasoning",
    "question_type": "{qtype}",
    "format": "multiple_choice",
    "difficulty": 3,
    "content": {{
      "text": "[Question text following the GL Assessment style]",
      "options": ["Option A", "Option B", "Option C", "Option D", "Option E"]
    }},
    "answer": {{ "value": "[Exact text of correct option]" }},
    "explanation": "[Why this is the correct answer]",
    "hints": [],
    "tags": ["{qtype}"],
    "source": "LLM Generated"
  }}
]

IMPORTANT: Answers must be correct. Use age-appropriate vocabulary. Vary correct answer position. Generate exactly {count} questions.""",
}


def get_prompt(subject: str, qtype: str, count: int) -> str:
    """Get the generation prompt for a subject/type combination."""
    key = (subject, qtype)
    if key in PROMPTS:
        template = PROMPTS[key]
    elif (subject, "_default") in PROMPTS:
        template = PROMPTS[(subject, "_default")]
    else:
        raise ValueError(f"No prompt template for {subject}/{qtype}")
    return template.format(count=count, qtype=qtype)


def generate_batch(subject: str, qtype: str, count: int) -> list[dict]:
    """Generate a batch of questions using Gemini."""
    prompt = get_prompt(subject, qtype, count)

    logger.info(f"Generating {count} {subject}/{qtype} questions...")

    text = None
    for attempt in range(5):
        try:
            response = gemini_client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.8,
                    response_mime_type="application/json",
                ),
            )
            text = response.text
            break
        except Exception as e:
            wait = DELAY_BETWEEN_BATCHES * (attempt + 1)
            logger.warning(f"  Attempt {attempt+1} failed: {e}")
            logger.info(f"  Waiting {wait}s before retry...")
            time.sleep(wait)

    if text is None:
        logger.error(f"  All attempts failed for {subject}/{qtype}")
        return []

    text = text.strip()
    # Handle potential JSON wrapping
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    parsed = json.loads(text)
    # Handle wrapped response
    if isinstance(parsed, dict):
        if "questions" in parsed:
            questions = parsed["questions"]
        else:
            # Try first list-valued key
            for v in parsed.values():
                if isinstance(v, list):
                    questions = v
                    break
            else:
                questions = []
    else:
        questions = parsed

    # Validate each question has required fields
    valid = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        if all(k in q for k in ("subject", "question_type", "content", "answer")):
            # Ensure content has options
            if isinstance(q["content"], dict) and q["content"].get("options"):
                # Ensure answer value matches one of the options
                answer_val = q["answer"].get("value", "")
                if answer_val in q["content"]["options"]:
                    valid.append(q)
                else:
                    logger.warning(
                        f"Answer '{answer_val}' not in options for: "
                        f"{q['content'].get('text', '')[:60]}..."
                    )
            else:
                logger.warning(f"Missing options in question: {q.get('content', {}).get('text', '')[:60]}")
        else:
            logger.warning(f"Missing required fields in question")

    logger.info(f"  Generated {len(questions)}, {len(valid)} valid")
    return valid


def main():
    output_dir = Path(__file__).parent.parent / "data" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load existing questions to know what we have
    dump_path = Path(__file__).parent.parent / "data" / "questions" / "deployment_dump.json"
    existing = []
    if dump_path.exists():
        with open(dump_path) as f:
            existing = json.load(f)

    # Count existing by subject+type
    existing_counts = {}
    for q in existing:
        key = (q["subject"], q["question_type"])
        existing_counts[key] = existing_counts.get(key, 0) + 1

    all_generated = []
    batch_size = 10  # Generate 10 at a time to stay within token limits

    # Load previously generated files to resume
    already_generated_counts = {}
    for gen_file in output_dir.glob("*.json"):
        if gen_file.name == "all_generated.json":
            continue
        try:
            with open(gen_file) as f:
                gen_qs = json.load(f)
            if gen_qs:
                key = (gen_qs[0]["subject"], gen_qs[0]["question_type"])
                already_generated_counts[key] = already_generated_counts.get(key, 0) + len(gen_qs)
                all_generated.extend(gen_qs)
                logger.info(f"Loaded {len(gen_qs)} previously generated from {gen_file.name}")
        except Exception:
            pass

    for (subject, qtype), target in TARGETS.items():
        have = existing_counts.get((subject, qtype), 0)
        have += already_generated_counts.get((subject, qtype), 0)
        need = max(0, target - have)

        if need == 0:
            logger.info(f"Already have {have}/{target} for {subject}/{qtype}, skipping")
            continue

        logger.info(f"Need {need} more {subject}/{qtype} (have {have}/{target})")

        generated_for_type = []
        remaining = need

        while remaining > 0:
            batch = min(batch_size, remaining)
            try:
                questions = generate_batch(subject, qtype, batch)
                generated_for_type.extend(questions)
                remaining -= len(questions)
                logger.info(f"  Progress: {len(generated_for_type)}/{need} for {subject}/{qtype}")

                # Rate limiting
                time.sleep(DELAY_BETWEEN_BATCHES)
            except Exception as e:
                logger.error(f"  Error generating {subject}/{qtype}: {e}")
                time.sleep(10)
                remaining -= batch  # Skip this batch to avoid infinite loop

        all_generated.extend(generated_for_type)

        # Save incrementally per type
        type_file = output_dir / f"{subject}_{qtype}.json"
        with open(type_file, "w") as f:
            json.dump(generated_for_type, f, indent=2)
        logger.info(f"Saved {len(generated_for_type)} {subject}/{qtype} to {type_file}")

    # Save all generated questions
    all_file = output_dir / "all_generated.json"
    with open(all_file, "w") as f:
        json.dump(all_generated, f, indent=2)

    logger.info(f"\nTotal generated: {len(all_generated)}")
    logger.info(f"Saved to: {all_file}")

    # Print summary
    from collections import Counter
    by_subject = Counter(q["subject"] for q in all_generated)
    by_type = Counter(q["question_type"] for q in all_generated)

    print("\n=== GENERATION SUMMARY ===")
    print(f"Total generated: {len(all_generated)}")
    print("\nBy subject:")
    for s, c in by_subject.most_common():
        print(f"  {s}: {c}")
    print("\nBy type:")
    for t, c in by_type.most_common():
        print(f"  {t}: {c}")


if __name__ == "__main__":
    main()
