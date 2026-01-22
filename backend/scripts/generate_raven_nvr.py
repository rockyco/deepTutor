#!/usr/bin/env python3
"""Generate NVR questions using raven-gen library.

This creates Raven's Progressive Matrices style questions - the gold standard
for non-verbal reasoning assessment.

Usage:
    uv run python scripts/generate_raven_nvr.py --count 50
    uv run python scripts/generate_raven_nvr.py --preview
"""

import argparse
import base64
import io
import json
import random
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Import raven-gen
from raven_gen import RavenGenerator, Matrix


def image_to_data_url(img: np.ndarray | Image.Image) -> str:
    """Convert image to base64 data URL."""
    if isinstance(img, np.ndarray):
        # Handle different dtypes
        if img.dtype == np.float64 or img.dtype == np.float32:
            img = (img * 255).astype(np.uint8)
        elif img.dtype != np.uint8:
            img = img.astype(np.uint8)

        # Handle different channel counts
        if len(img.shape) == 2:
            pil_img = Image.fromarray(img, mode='L')
        elif img.shape[2] == 3:
            pil_img = Image.fromarray(img, mode='RGB')
        elif img.shape[2] == 4:
            pil_img = Image.fromarray(img, mode='RGBA')
        else:
            pil_img = Image.fromarray(img)
    else:
        pil_img = img

    # Convert to PNG bytes
    buffer = io.BytesIO()
    pil_img.save(buffer, format='PNG')
    buffer.seek(0)

    # Encode to base64
    encoded = base64.b64encode(buffer.read()).decode()
    return f"data:image/png;base64,{encoded}"


def create_matrix_display(matrix: Matrix) -> str:
    """Create a display image showing the 3x3 matrix with ? in bottom-right."""
    # Get the rendered images from the matrix
    # matrix.render() gives us all images including the problem and answers

    # The matrix has context (8 images) and choices (8 images)
    context_imgs = matrix.context  # List of 8 numpy arrays

    # Create a 3x3 grid canvas
    cell_size = 100
    padding = 5
    grid_size = cell_size * 3 + padding * 4

    # Create white canvas
    canvas = Image.new('RGB', (grid_size, grid_size), color='white')
    draw = ImageDraw.Draw(canvas)

    # Draw grid lines
    for i in range(4):
        pos = i * (cell_size + padding)
        draw.line([(pos, 0), (pos, grid_size)], fill='gray', width=2)
        draw.line([(0, pos), (grid_size, pos)], fill='gray', width=2)

    # Place first 8 context images (last one is the answer position)
    for i in range(8):
        row = i // 3
        col = i % 3

        x = col * (cell_size + padding) + padding
        y = row * (cell_size + padding) + padding

        # Get and resize image
        img_array = context_imgs[i]
        if img_array.dtype != np.uint8:
            img_array = (img_array * 255).astype(np.uint8)

        if len(img_array.shape) == 2:
            img = Image.fromarray(img_array, mode='L').convert('RGB')
        else:
            img = Image.fromarray(img_array)

        img = img.resize((cell_size, cell_size), Image.Resampling.LANCZOS)
        canvas.paste(img, (x, y))

    # Draw "?" in the 9th position (bottom-right)
    x = 2 * (cell_size + padding) + padding + cell_size // 2
    y = 2 * (cell_size + padding) + padding + cell_size // 2

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
    except:
        font = ImageFont.load_default()

    draw.text((x - 15, y - 35), "?", fill='blue', font=font)

    return image_to_data_url(canvas)


def generate_question(difficulty: int = 2) -> dict | None:
    """Generate a single RAVEN-style question."""
    try:
        # Create generator with appropriate difficulty
        # difficulty 1-5 maps to different rule complexities
        gen = RavenGenerator(
            n_rows=3,
            n_cols=3,
            n_choices=4,  # 4 answer choices (A, B, C, D)
        )

        # Generate a matrix
        matrix = gen.generate()

        if matrix is None:
            return None

        # Get the answer choices
        choices = matrix.choices  # List of numpy arrays
        correct_idx = matrix.answer  # Index of correct answer

        # Create the matrix display image
        matrix_image = create_matrix_display(matrix)

        # Convert choices to data URLs
        options = []
        for choice in choices:
            if choice.dtype != np.uint8:
                choice = (choice * 255).astype(np.uint8)
            if len(choice.shape) == 2:
                img = Image.fromarray(choice, mode='L')
            else:
                img = Image.fromarray(choice)
            img = img.resize((100, 100), Image.Resampling.LANCZOS)
            options.append(image_to_data_url(img))

        # The correct answer is the option at correct_idx
        correct_answer = options[correct_idx]

        return {
            "id": str(uuid.uuid4()),
            "subject": "non_verbal_reasoning",
            "question_type": "nvr_matrices",
            "format": "multiple_choice",
            "difficulty": difficulty,
            "content": {
                "text": "Look at the pattern in the matrix. Which option completes it?",
                "image_url": matrix_image,
                "options": options,
            },
            "answer": {
                "value": correct_answer,
                "accept_variations": None,
                "case_sensitive": False,
                "order_matters": True,
            },
            "explanation": "Analyze the rows and columns to find the transformation pattern. The correct answer follows the same rules.",
            "hints": [
                {"level": 1, "text": "Look at each row - what changes between cells?", "penalty": 0.1},
                {"level": 2, "text": "Check the columns and diagonals for additional patterns.", "penalty": 0.2},
            ],
            "tags": ["matrices", "patterns", "visual_reasoning", "raven"],
            "source": "raven_gen",
            "created_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        print(f"Error generating question: {e}")
        return None


def generate_questions(count: int = 50) -> list[dict]:
    """Generate multiple RAVEN-style questions."""
    questions = []
    attempts = 0
    max_attempts = count * 3  # Allow some failures

    while len(questions) < count and attempts < max_attempts:
        attempts += 1
        # Vary difficulty
        difficulty = random.choices([1, 2, 3, 4], weights=[0.2, 0.3, 0.3, 0.2])[0]

        q = generate_question(difficulty)
        if q:
            questions.append(q)
            if len(questions) % 10 == 0:
                print(f"Generated {len(questions)}/{count} questions...")

    return questions


def save_to_database(questions: list[dict]):
    """Save questions to the database."""
    db_path = Path("data/tutor.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # First, delete any existing raven_gen questions
    cursor.execute("DELETE FROM questions WHERE source = 'raven_gen'")
    deleted = cursor.rowcount
    if deleted:
        print(f"Deleted {deleted} existing raven_gen questions")

    for q in questions:
        cursor.execute(
            """
            INSERT INTO questions (id, subject, question_type, format, difficulty,
                                   content, answer, explanation, hints, tags, source, created_at)
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
            ),
        )

    conn.commit()
    print(f"Saved {len(questions)} questions to database")

    # Show total NVR count
    cursor.execute("SELECT COUNT(*) FROM questions WHERE subject = 'non_verbal_reasoning'")
    total = cursor.fetchone()[0]
    print(f"Total NVR questions in database: {total}")

    conn.close()


def preview_question():
    """Generate and display a sample question in browser."""
    import webbrowser
    import tempfile

    print("Generating sample question...")
    q = generate_question(difficulty=2)

    if not q:
        print("Failed to generate question")
        return

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>RAVEN NVR Question Preview</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .matrix {{ margin: 20px 0; }}
            .matrix img {{ max-width: 400px; border: 2px solid #333; }}
            .options {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 20px 0; }}
            .option {{ border: 2px solid #ccc; padding: 10px; text-align: center; cursor: pointer; }}
            .option:hover {{ border-color: #007bff; }}
            .option img {{ width: 100%; }}
            .correct {{ border-color: green; background: #e8f5e9; }}
            h2 {{ color: #333; }}
        </style>
    </head>
    <body>
        <h1>RAVEN-Style NVR Question</h1>
        <h2>{q['content']['text']}</h2>

        <div class="matrix">
            <img src="{q['content']['image_url']}" alt="Matrix">
        </div>

        <h3>Choose the answer:</h3>
        <div class="options">
    """

    for i, opt in enumerate(q['content']['options']):
        is_correct = opt == q['answer']['value']
        correct_class = 'correct' if is_correct else ''
        label = chr(65 + i)  # A, B, C, D
        html += f"""
            <div class="option {correct_class}">
                <img src="{opt}" alt="Option {label}">
                <p>{label}{' (Correct)' if is_correct else ''}</p>
            </div>
        """

    html += """
        </div>
        <p><strong>Explanation:</strong> """ + q['explanation'] + """</p>
    </body>
    </html>
    """

    # Write to temp file and open in browser
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(html)
        webbrowser.open(f'file://{f.name}')
        print(f"Preview opened in browser: {f.name}")


def main():
    parser = argparse.ArgumentParser(description="Generate RAVEN-style NVR questions")
    parser.add_argument("--count", type=int, default=50, help="Number of questions to generate")
    parser.add_argument("--preview", action="store_true", help="Preview a sample question")
    args = parser.parse_args()

    if args.preview:
        preview_question()
        return

    print(f"Generating {args.count} RAVEN-style NVR questions...")
    questions = generate_questions(args.count)

    if questions:
        save_to_database(questions)
    else:
        print("No questions generated")


if __name__ == "__main__":
    main()
