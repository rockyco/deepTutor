#!/usr/bin/env python3
"""Import NVR questions from the RAVEN dataset.

RAVEN (Relational and Analogical Visual rEasoNing) contains 70,000 matrix-style
visual reasoning problems - similar to Raven's Progressive Matrices.

Dataset: https://github.com/WellyZhang/RAVEN
Paper: https://arxiv.org/abs/1903.02741

Usage:
    uv run python scripts/import_raven_nvr.py --count 100
    uv run python scripts/import_raven_nvr.py --download  # Download dataset first
"""

import argparse
import base64
import io
import json
import os
import random
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image


# RAVEN configurations and their descriptions
RAVEN_CONFIGS = {
    "center_single": "Single centered shape",
    "distribute_four": "Four shapes in 2x2 grid",
    "distribute_nine": "Nine shapes in 3x3 grid",
    "left_right": "Shapes positioned horizontally",
    "up_down": "Shapes positioned vertically",
    "in_center_single_out_center_single": "Nested center shapes",
    "in_distribute_four_out_center_single": "Nested grid shapes",
}

RAVEN_DIR = Path("data/raven")


def download_raven_sample():
    """Download a sample of the RAVEN dataset."""
    import gdown

    RAVEN_DIR.mkdir(parents=True, exist_ok=True)

    # Google Drive file ID for RAVEN-10000 (smaller version)
    # Full dataset: https://drive.google.com/drive/folders/111swnmzAG-R-WYrxBZ0KjJC0lFKb9KlW
    # Using center_single as it's simplest
    file_id = "1SxSGOYlGCPQfNnznhKPtjRrn-o5O1j2F"  # center_single.zip
    output = RAVEN_DIR / "center_single.zip"

    if not output.exists():
        print(f"Downloading RAVEN center_single to {output}...")
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, str(output), quiet=False)

        # Extract
        import zipfile
        with zipfile.ZipFile(output, 'r') as zip_ref:
            zip_ref.extractall(RAVEN_DIR)
        print("Extracted successfully")
    else:
        print(f"Dataset already exists at {output}")


def image_to_data_url(img_array: np.ndarray) -> str:
    """Convert numpy image array to base64 data URL."""
    # Ensure proper uint8 format
    if img_array.dtype != np.uint8:
        img_array = (img_array * 255).astype(np.uint8)

    # Create PIL image
    img = Image.fromarray(img_array, mode='L')  # Grayscale

    # Convert to PNG bytes
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    # Encode to base64
    encoded = base64.b64encode(buffer.read()).decode()
    return f"data:image/png;base64,{encoded}"


def create_matrix_image(images: list[np.ndarray]) -> str:
    """Create a 3x3 matrix image with the 8th cell marked with '?'."""
    # Each image is 160x160, create 3x3 grid
    cell_size = 160
    grid_size = cell_size * 3

    # Create blank canvas
    canvas = np.ones((grid_size, grid_size), dtype=np.uint8) * 255

    # Place first 8 images (row-major order)
    for i, img in enumerate(images[:8]):
        if i == 8:  # Skip the 9th position (it's the question mark)
            break
        row = i // 3
        col = i % 3
        y_start = row * cell_size
        x_start = col * cell_size
        canvas[y_start:y_start+cell_size, x_start:x_start+cell_size] = img

    # Add question mark in position 8 (bottom right)
    # Draw a simple "?" symbol
    from PIL import Image, ImageDraw, ImageFont
    img = Image.fromarray(canvas, mode='L')
    draw = ImageDraw.Draw(img)

    # Position for question mark (center of bottom-right cell)
    x = 2 * cell_size + cell_size // 2
    y = 2 * cell_size + cell_size // 2

    # Draw question mark
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
    except:
        font = ImageFont.load_default()

    draw.text((x-20, y-50), "?", fill=128, font=font)

    return image_to_data_url(np.array(img))


def load_raven_problem(npz_path: Path) -> dict | None:
    """Load a single RAVEN problem from NPZ file."""
    try:
        data = np.load(npz_path)

        # Images: (16, 160, 160) - first 8 are matrix, last 8 are choices
        images = data["image"]
        target = int(data["target"])  # Correct answer index (0-7)

        # Split into matrix images and answer choices
        matrix_images = [images[i] for i in range(8)]
        answer_choices = [images[i+8] for i in range(8)]

        return {
            "matrix": matrix_images,
            "choices": answer_choices,
            "answer_index": target,
        }
    except Exception as e:
        print(f"Error loading {npz_path}: {e}")
        return None


def convert_to_db_format(problem: dict, config_name: str) -> dict:
    """Convert RAVEN problem to our database format."""
    # Create the main matrix image (3x3 with question mark)
    matrix_image = create_matrix_image(problem["matrix"])

    # Convert answer choices to data URLs
    options = [image_to_data_url(img) for img in problem["choices"]]

    # The correct answer is the option at answer_index
    correct_answer = options[problem["answer_index"]]

    # Difficulty based on config complexity
    difficulty_map = {
        "center_single": 1,
        "left_right": 2,
        "up_down": 2,
        "distribute_four": 3,
        "in_center_single_out_center_single": 3,
        "distribute_nine": 4,
        "in_distribute_four_out_center_single": 4,
    }
    difficulty = difficulty_map.get(config_name, 3)

    return {
        "id": str(uuid.uuid4()),
        "subject": "non_verbal_reasoning",
        "question_type": "nvr_matrices",
        "format": "multiple_choice",
        "difficulty": difficulty,
        "content": {
            "text": "Look at the pattern in the matrix. Which option completes it?",
            "image_url": matrix_image,  # The 3x3 matrix with "?"
            "options": options,  # 8 answer choices
        },
        "answer": {
            "value": correct_answer,
            "accept_variations": None,
            "case_sensitive": False,
            "order_matters": True,
        },
        "explanation": "Study the rows and columns to find the pattern. The correct answer follows the same transformation rules.",
        "hints": [
            {"level": 1, "text": "Look at each row - what changes from left to right?", "penalty": 0.1},
            {"level": 2, "text": "Check the columns too - patterns often work both ways.", "penalty": 0.2},
        ],
        "tags": ["matrices", "patterns", "visual_reasoning", "raven"],
        "source": "raven_dataset",
        "created_at": datetime.utcnow().isoformat(),
    }


def import_questions(count: int = 100, config: str = "center_single"):
    """Import questions from RAVEN dataset."""
    config_dir = RAVEN_DIR / config

    if not config_dir.exists():
        print(f"Config directory not found: {config_dir}")
        print("Run with --download first to get the dataset")
        return []

    # Find all npz files
    npz_files = list(config_dir.glob("**/*.npz"))
    if not npz_files:
        print(f"No NPZ files found in {config_dir}")
        return []

    print(f"Found {len(npz_files)} problems in {config}")

    # Sample randomly
    sample_files = random.sample(npz_files, min(count, len(npz_files)))

    questions = []
    for npz_path in sample_files:
        problem = load_raven_problem(npz_path)
        if problem:
            question = convert_to_db_format(problem, config)
            questions.append(question)

    print(f"Converted {len(questions)} questions")
    return questions


def save_to_database(questions: list[dict]):
    """Save questions to the database."""
    db_path = Path("data/tutor.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

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

    # Show total count
    cursor.execute("SELECT COUNT(*) FROM questions WHERE source = 'raven_dataset'")
    total = cursor.fetchone()[0]
    print(f"Total RAVEN questions in database: {total}")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Import NVR questions from RAVEN dataset")
    parser.add_argument("--download", action="store_true", help="Download the dataset first")
    parser.add_argument("--count", type=int, default=100, help="Number of questions to import")
    parser.add_argument("--config", type=str, default="center_single",
                        choices=list(RAVEN_CONFIGS.keys()),
                        help="RAVEN configuration to use")
    args = parser.parse_args()

    if args.download:
        download_raven_sample()
        return

    questions = import_questions(args.count, args.config)
    if questions:
        save_to_database(questions)


if __name__ == "__main__":
    main()
