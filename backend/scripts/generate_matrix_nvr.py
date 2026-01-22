#!/usr/bin/env python3
"""Generate proper Raven's Progressive Matrices style NVR questions.

Creates 3x3 matrix puzzles where users must identify the missing piece
by understanding the transformation rules applied to rows/columns.

Usage:
    uv run python scripts/generate_matrix_nvr.py --count 50
    uv run python scripts/generate_matrix_nvr.py --preview
"""

import argparse
import base64
import io
import json
import random
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw


# Shape drawing functions
def draw_circle(draw: ImageDraw, x: int, y: int, size: int, fill: str, outline: str):
    draw.ellipse([x - size//2, y - size//2, x + size//2, y + size//2],
                 fill=fill, outline=outline, width=2)


def draw_square(draw: ImageDraw, x: int, y: int, size: int, fill: str, outline: str):
    draw.rectangle([x - size//2, y - size//2, x + size//2, y + size//2],
                   fill=fill, outline=outline, width=2)


def draw_triangle(draw: ImageDraw, x: int, y: int, size: int, fill: str, outline: str):
    points = [
        (x, y - size//2),
        (x - size//2, y + size//2),
        (x + size//2, y + size//2)
    ]
    draw.polygon(points, fill=fill, outline=outline, width=2)


def draw_diamond(draw: ImageDraw, x: int, y: int, size: int, fill: str, outline: str):
    points = [
        (x, y - size//2),
        (x + size//2, y),
        (x, y + size//2),
        (x - size//2, y)
    ]
    draw.polygon(points, fill=fill, outline=outline, width=2)


def draw_pentagon(draw: ImageDraw, x: int, y: int, size: int, fill: str, outline: str):
    import math
    points = []
    for i in range(5):
        angle = math.radians(i * 72 - 90)
        px = x + int(size//2 * math.cos(angle))
        py = y + int(size//2 * math.sin(angle))
        points.append((px, py))
    draw.polygon(points, fill=fill, outline=outline, width=2)


def draw_hexagon(draw: ImageDraw, x: int, y: int, size: int, fill: str, outline: str):
    import math
    points = []
    for i in range(6):
        angle = math.radians(i * 60 - 90)
        px = x + int(size//2 * math.cos(angle))
        py = y + int(size//2 * math.sin(angle))
        points.append((px, py))
    draw.polygon(points, fill=fill, outline=outline, width=2)


def draw_cross(draw: ImageDraw, x: int, y: int, size: int, fill: str, outline: str):
    arm_width = size // 4
    # Vertical bar
    draw.rectangle([x - arm_width//2, y - size//2, x + arm_width//2, y + size//2],
                   fill=fill, outline=outline, width=2)
    # Horizontal bar
    draw.rectangle([x - size//2, y - arm_width//2, x + size//2, y + arm_width//2],
                   fill=fill, outline=outline, width=2)


def draw_star(draw: ImageDraw, x: int, y: int, size: int, fill: str, outline: str):
    import math
    outer_r = size // 2
    inner_r = size // 4
    points = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        r = outer_r if i % 2 == 0 else inner_r
        px = x + int(r * math.cos(angle))
        py = y + int(r * math.sin(angle))
        points.append((px, py))
    draw.polygon(points, fill=fill, outline=outline, width=2)


SHAPES = {
    'circle': draw_circle,
    'square': draw_square,
    'triangle': draw_triangle,
    'diamond': draw_diamond,
    'pentagon': draw_pentagon,
    'hexagon': draw_hexagon,
    'cross': draw_cross,
    'star': draw_star,
}

COLORS = ['black', 'gray', 'white']
SIZES = [20, 30, 40]


@dataclass
class CellContent:
    """Content of a single cell in the matrix."""
    shape: str
    fill: str
    size: int
    count: int = 1  # Number of shapes in cell
    rotation: int = 0  # Rotation in degrees


def render_cell(content: CellContent, cell_size: int = 80) -> Image.Image:
    """Render a single cell."""
    img = Image.new('RGB', (cell_size, cell_size), color='white')
    draw = ImageDraw.Draw(img)

    # Draw border
    draw.rectangle([0, 0, cell_size-1, cell_size-1], outline='black', width=1)

    if content.shape and content.shape in SHAPES:
        cx, cy = cell_size // 2, cell_size // 2

        # Handle multiple shapes
        positions = [(cx, cy)]
        if content.count == 2:
            positions = [(cx - 15, cy), (cx + 15, cy)]
        elif content.count == 3:
            positions = [(cx, cy - 15), (cx - 15, cy + 10), (cx + 15, cy + 10)]

        fill_color = content.fill if content.fill != 'white' else None
        outline_color = 'black'

        for px, py in positions:
            SHAPES[content.shape](draw, px, py, content.size, fill_color, outline_color)

    return img


def create_matrix_image(cells: list[CellContent], cell_size: int = 80) -> Image.Image:
    """Create a 3x3 matrix image from 9 cells (last one shows '?')."""
    grid_size = cell_size * 3
    img = Image.new('RGB', (grid_size, grid_size), color='white')

    for i, content in enumerate(cells[:8]):  # First 8 cells
        row, col = i // 3, i % 3
        cell_img = render_cell(content, cell_size)
        img.paste(cell_img, (col * cell_size, row * cell_size))

    # Draw "?" in position 8 (bottom-right)
    draw = ImageDraw.Draw(img)
    x = 2 * cell_size + cell_size // 2
    y = 2 * cell_size + cell_size // 2

    # Draw cell border
    draw.rectangle([2 * cell_size, 2 * cell_size, 3 * cell_size - 1, 3 * cell_size - 1],
                   outline='black', width=1)

    try:
        from PIL import ImageFont
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    except:
        font = None

    draw.text((x - 12, y - 25), "?", fill='blue', font=font)

    return img


def image_to_data_url(img: Image.Image) -> str:
    """Convert PIL Image to base64 data URL."""
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    encoded = base64.b64encode(buffer.read()).decode()
    return f"data:image/png;base64,{encoded}"


# Rule-based matrix generation

class MatrixRule:
    """Base class for matrix transformation rules."""

    def apply_row(self, row: list[CellContent]) -> list[CellContent]:
        """Apply rule across a row."""
        raise NotImplementedError


class ConstantRule(MatrixRule):
    """Same content in each cell of the row."""

    def generate_row(self) -> list[CellContent]:
        shape = random.choice(list(SHAPES.keys()))
        fill = random.choice(COLORS)
        size = random.choice(SIZES)
        return [CellContent(shape, fill, size) for _ in range(3)]


class ProgressionRule(MatrixRule):
    """Content changes progressively across the row."""

    def __init__(self, attribute: str):
        self.attribute = attribute  # 'size', 'fill', 'count'

    def generate_row(self) -> list[CellContent]:
        shape = random.choice(list(SHAPES.keys()))

        if self.attribute == 'size':
            sizes = [20, 30, 40]
            fill = random.choice(['black', 'gray'])
            return [CellContent(shape, fill, s) for s in sizes]

        elif self.attribute == 'fill':
            fills = ['white', 'gray', 'black']
            size = random.choice(SIZES)
            return [CellContent(shape, f, size) for f in fills]

        elif self.attribute == 'count':
            counts = [1, 2, 3]
            fill = random.choice(['black', 'gray'])
            size = 20  # Smaller for multiple shapes
            return [CellContent(shape, fill, size, count=c) for c in counts]

        return [CellContent(shape, 'black', 30) for _ in range(3)]


class DistributionRule(MatrixRule):
    """Different shapes/fills in each cell, each appearing once per row."""

    def __init__(self, attribute: str):
        self.attribute = attribute  # 'shape' or 'fill'

    def generate_row(self) -> list[CellContent]:
        size = random.choice(SIZES)

        if self.attribute == 'shape':
            shapes = random.sample(list(SHAPES.keys()), 3)
            fill = random.choice(['black', 'gray'])
            return [CellContent(s, fill, size) for s in shapes]

        elif self.attribute == 'fill':
            shape = random.choice(list(SHAPES.keys()))
            fills = ['white', 'gray', 'black']
            random.shuffle(fills)
            return [CellContent(shape, f, size) for f in fills]

        return [CellContent('circle', 'black', size) for _ in range(3)]


def generate_matrix() -> tuple[list[CellContent], CellContent, str]:
    """Generate a complete matrix with answer and explanation."""
    # Choose a rule type
    rule_type = random.choice([
        ('constant', ConstantRule()),
        ('size_progression', ProgressionRule('size')),
        ('fill_progression', ProgressionRule('fill')),
        ('count_progression', ProgressionRule('count')),
        ('shape_distribution', DistributionRule('shape')),
        ('fill_distribution', DistributionRule('fill')),
    ])

    rule_name, rule = rule_type

    # Generate 3 rows following the rule
    rows = []
    for _ in range(3):
        row = rule.generate_row()
        rows.append(row)

    # Flatten to 9 cells
    cells = [cell for row in rows for cell in row]

    # The answer is the 9th cell (index 8)
    answer = cells[8]

    # Create explanation based on rule
    explanations = {
        'constant': "Each row contains the same shape with identical properties.",
        'size_progression': "The shapes increase in size from left to right in each row.",
        'fill_progression': "The fill changes from light to dark across each row.",
        'count_progression': "The number of shapes increases from left to right.",
        'shape_distribution': "Each row contains three different shapes.",
        'fill_distribution': "Each row contains three different fills (white, gray, black).",
    }

    return cells, answer, explanations.get(rule_name, "Analyze the pattern in rows and columns.")


def generate_distractors(answer: CellContent, count: int = 3) -> list[CellContent]:
    """Generate plausible wrong answers."""
    distractors = []

    # Wrong shape
    other_shapes = [s for s in SHAPES.keys() if s != answer.shape]
    if other_shapes:
        distractors.append(CellContent(
            random.choice(other_shapes),
            answer.fill,
            answer.size,
            answer.count
        ))

    # Wrong fill
    other_fills = [f for f in COLORS if f != answer.fill]
    if other_fills:
        distractors.append(CellContent(
            answer.shape,
            random.choice(other_fills),
            answer.size,
            answer.count
        ))

    # Wrong size
    other_sizes = [s for s in SIZES if s != answer.size]
    if other_sizes:
        distractors.append(CellContent(
            answer.shape,
            answer.fill,
            random.choice(other_sizes),
            answer.count
        ))

    # Wrong count
    other_counts = [c for c in [1, 2, 3] if c != answer.count]
    if other_counts:
        distractors.append(CellContent(
            answer.shape,
            answer.fill,
            answer.size,
            random.choice(other_counts)
        ))

    # Shuffle and return requested count
    random.shuffle(distractors)
    return distractors[:count]


def generate_question(difficulty: int = 2) -> dict:
    """Generate a single matrix NVR question."""
    cells, answer, explanation = generate_matrix()

    # Create matrix image (first 8 cells + "?" for 9th)
    matrix_img = create_matrix_image(cells)
    matrix_url = image_to_data_url(matrix_img)

    # Create answer option
    answer_img = render_cell(answer)
    answer_url = image_to_data_url(answer_img)

    # Create distractors
    distractors = generate_distractors(answer, count=3)
    distractor_urls = [image_to_data_url(render_cell(d)) for d in distractors]

    # Shuffle options
    options = [answer_url] + distractor_urls
    random.shuffle(options)

    return {
        "id": str(uuid.uuid4()),
        "subject": "non_verbal_reasoning",
        "question_type": "nvr_matrices",
        "format": "multiple_choice",
        "difficulty": difficulty,
        "content": {
            "text": "Look at the pattern in the matrix. Which option completes it?",
            "image_url": matrix_url,
            "options": options,
        },
        "answer": {
            "value": answer_url,
            "accept_variations": None,
            "case_sensitive": False,
            "order_matters": True,
        },
        "explanation": explanation,
        "hints": [
            {"level": 1, "text": "Look at each row - what stays the same or changes?", "penalty": 0.1},
            {"level": 2, "text": "Check the columns too for additional patterns.", "penalty": 0.2},
        ],
        "tags": ["matrices", "patterns", "visual_reasoning"],
        "source": "matrix_generator",
        "created_at": datetime.utcnow().isoformat(),
    }


def generate_questions(count: int = 50) -> list[dict]:
    """Generate multiple matrix questions."""
    questions = []

    for i in range(count):
        # Vary difficulty
        difficulty = random.choices([1, 2, 3, 4], weights=[0.2, 0.3, 0.3, 0.2])[0]
        q = generate_question(difficulty)
        questions.append(q)

        if (i + 1) % 10 == 0:
            print(f"Generated {i + 1}/{count} questions...")

    return questions


def save_to_database(questions: list[dict]):
    """Save questions to the database."""
    db_path = Path("data/tutor.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Delete existing matrix_generator questions
    cursor.execute("DELETE FROM questions WHERE source = 'matrix_generator'")
    deleted = cursor.rowcount
    if deleted:
        print(f"Deleted {deleted} existing matrix questions")

    # Also delete the old generated_nvr questions (from simple SVG generator)
    cursor.execute("DELETE FROM questions WHERE source = 'generated_nvr'")
    deleted = cursor.rowcount
    if deleted:
        print(f"Deleted {deleted} old NVR questions")

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

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Matrix NVR Question Preview</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
            .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .matrix {{ margin: 20px 0; text-align: center; }}
            .matrix img {{ max-width: 300px; border: 2px solid #333; }}
            .options {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
            .option {{ border: 2px solid #ccc; padding: 10px; text-align: center; cursor: pointer; background: white; border-radius: 8px; }}
            .option:hover {{ border-color: #007bff; }}
            .option img {{ width: 60px; height: 60px; }}
            .correct {{ border-color: #28a745 !important; background: #e8f5e9; }}
            h2 {{ color: #333; margin-top: 0; }}
            .explanation {{ background: #e3f2fd; padding: 15px; border-radius: 8px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="card">
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
        label = chr(65 + i)
        html += f"""
                <div class="option {correct_class}">
                    <img src="{opt}" alt="Option {label}">
                    <p><strong>{label}</strong>{' ✓' if is_correct else ''}</p>
                </div>
        """

    html += f"""
            </div>
            <div class="explanation">
                <strong>Explanation:</strong> {q['explanation']}
            </div>
        </div>
    </body>
    </html>
    """

    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(html)
        webbrowser.open(f'file://{f.name}')
        print(f"Preview opened: {f.name}")


def main():
    parser = argparse.ArgumentParser(description="Generate Matrix-style NVR questions")
    parser.add_argument("--count", type=int, default=50, help="Number of questions to generate")
    parser.add_argument("--preview", action="store_true", help="Preview a sample question")
    args = parser.parse_args()

    if args.preview:
        preview_question()
        return

    print(f"Generating {args.count} matrix NVR questions...")
    questions = generate_questions(args.count)

    if questions:
        save_to_database(questions)


if __name__ == "__main__":
    main()
