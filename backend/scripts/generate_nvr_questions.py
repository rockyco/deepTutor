#!/usr/bin/env python3
"""Generate Non-Verbal Reasoning questions with SVG shapes.

This prototype generates various NVR question types:
- Sequences (pattern continuation)
- Odd one out
- Analogies (A is to B as C is to ?)
- Rotation
- Reflection

Usage:
    uv run python scripts/generate_nvr_questions.py --type sequences --count 10
    uv run python scripts/generate_nvr_questions.py --all --count 5
    uv run python scripts/generate_nvr_questions.py --preview  # Show sample in browser
"""

import argparse
import base64
import json
import math
import random
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import drawsvg as draw


# Shape colors
COLORS = ['#3B82F6', '#EF4444', '#22C55E', '#F59E0B', '#8B5CF6', '#EC4899']
FILL_PATTERNS = ['solid', 'striped', 'dotted', 'empty']


@dataclass
class Shape:
    """Represents a drawable shape."""
    shape_type: str  # circle, square, triangle, pentagon, hexagon, star
    x: float
    y: float
    size: float
    rotation: float = 0  # degrees
    color: str = '#3B82F6'
    fill_pattern: str = 'solid'


def draw_shape(d: draw.Drawing, shape: Shape):
    """Draw a shape on the canvas."""
    g = draw.Group(transform=f'translate({shape.x},{shape.y}) rotate({shape.rotation})')

    fill = shape.color if shape.fill_pattern == 'solid' else 'none'
    stroke = shape.color
    stroke_width = 2

    if shape.shape_type == 'circle':
        g.append(draw.Circle(0, 0, shape.size/2, fill=fill, stroke=stroke, stroke_width=stroke_width))
        if shape.fill_pattern == 'striped':
            for i in range(-int(shape.size/2), int(shape.size/2), 6):
                g.append(draw.Line(i, -shape.size/2, i, shape.size/2, stroke=stroke, stroke_width=1))
        elif shape.fill_pattern == 'dotted':
            for dx in range(-int(shape.size/3), int(shape.size/3)+1, 8):
                for dy in range(-int(shape.size/3), int(shape.size/3)+1, 8):
                    if dx*dx + dy*dy < (shape.size/2)**2:
                        g.append(draw.Circle(dx, dy, 2, fill=stroke))

    elif shape.shape_type == 'square':
        g.append(draw.Rectangle(-shape.size/2, -shape.size/2, shape.size, shape.size,
                                fill=fill, stroke=stroke, stroke_width=stroke_width))
        if shape.fill_pattern == 'striped':
            for i in range(-int(shape.size/2), int(shape.size/2), 6):
                g.append(draw.Line(i, -shape.size/2, i, shape.size/2, stroke=stroke, stroke_width=1))
        elif shape.fill_pattern == 'dotted':
            for dx in range(-int(shape.size/3), int(shape.size/3)+1, 8):
                for dy in range(-int(shape.size/3), int(shape.size/3)+1, 8):
                    g.append(draw.Circle(dx, dy, 2, fill=stroke))

    elif shape.shape_type == 'triangle':
        points = []
        for i in range(3):
            angle = math.radians(i * 120 - 90)
            points.extend([math.cos(angle) * shape.size/2, math.sin(angle) * shape.size/2])
        g.append(draw.Lines(*points, close=True, fill=fill, stroke=stroke, stroke_width=stroke_width))

    elif shape.shape_type == 'pentagon':
        points = []
        for i in range(5):
            angle = math.radians(i * 72 - 90)
            points.extend([math.cos(angle) * shape.size/2, math.sin(angle) * shape.size/2])
        g.append(draw.Lines(*points, close=True, fill=fill, stroke=stroke, stroke_width=stroke_width))

    elif shape.shape_type == 'hexagon':
        points = []
        for i in range(6):
            angle = math.radians(i * 60 - 90)
            points.extend([math.cos(angle) * shape.size/2, math.sin(angle) * shape.size/2])
        g.append(draw.Lines(*points, close=True, fill=fill, stroke=stroke, stroke_width=stroke_width))

    elif shape.shape_type == 'star':
        points = []
        for i in range(10):
            angle = math.radians(i * 36 - 90)
            r = shape.size/2 if i % 2 == 0 else shape.size/4
            points.extend([math.cos(angle) * r, math.sin(angle) * r])
        g.append(draw.Lines(*points, close=True, fill=fill, stroke=stroke, stroke_width=stroke_width))

    elif shape.shape_type == 'diamond':
        points = [0, -shape.size/2, shape.size/2, 0, 0, shape.size/2, -shape.size/2, 0]
        g.append(draw.Lines(*points, close=True, fill=fill, stroke=stroke, stroke_width=stroke_width))

    elif shape.shape_type == 'arrow':
        # Arrow pointing up
        points = [0, -shape.size/2, shape.size/3, 0, shape.size/6, 0,
                  shape.size/6, shape.size/2, -shape.size/6, shape.size/2,
                  -shape.size/6, 0, -shape.size/3, 0]
        g.append(draw.Lines(*points, close=True, fill=fill, stroke=stroke, stroke_width=stroke_width))

    d.append(g)


def create_shape_svg(shapes: list[Shape], width: int = 100, height: int = 100) -> str:
    """Create an SVG string from a list of shapes."""
    d = draw.Drawing(width, height)
    d.append(draw.Rectangle(0, 0, width, height, fill='white'))
    for shape in shapes:
        draw_shape(d, shape)
    return d.as_svg()


def svg_to_data_url(svg_string: str) -> str:
    """Convert SVG string to data URL for embedding in HTML/JSON."""
    encoded = base64.b64encode(svg_string.encode()).decode()
    return f"data:image/svg+xml;base64,{encoded}"


# Question Generators

def generate_sequence_question() -> dict:
    """Generate a sequence continuation question.

    Pattern: shapes follow a rule (rotation, color change, size change, etc.)
    """
    shape_types = ['circle', 'square', 'triangle', 'pentagon', 'hexagon', 'star', 'diamond']

    # Choose a pattern type
    pattern_type = random.choice(['rotation', 'color_cycle', 'shape_cycle', 'size_change'])

    base_shape = random.choice(shape_types)
    base_color = random.choice(COLORS)
    base_size = 40

    sequence_images = []

    if pattern_type == 'rotation':
        rotation_step = random.choice([45, 90, 30, 60])
        for i in range(4):  # 3 shown + 1 answer
            shape = Shape(base_shape, 50, 50, base_size, rotation=i * rotation_step, color=base_color)
            sequence_images.append(create_shape_svg([shape]))

        # Generate distractors (wrong rotations)
        correct_rotation = 3 * rotation_step
        wrong_rotations = [correct_rotation + 45, correct_rotation - 45, correct_rotation + 90]
        distractors = []
        for rot in wrong_rotations:
            shape = Shape(base_shape, 50, 50, base_size, rotation=rot, color=base_color)
            distractors.append(create_shape_svg([shape]))

        explanation = f"The shape rotates {rotation_step} degrees each step. After 3 rotations of {rotation_step} degrees, the total rotation is {correct_rotation} degrees."

    elif pattern_type == 'color_cycle':
        color_sequence = random.sample(COLORS, 4)
        for i, color in enumerate(color_sequence):
            shape = Shape(base_shape, 50, 50, base_size, color=color)
            sequence_images.append(create_shape_svg([shape]))

        # Distractors: wrong colors
        remaining_colors = [c for c in COLORS if c not in color_sequence]
        distractors = []
        for color in remaining_colors[:3]:
            shape = Shape(base_shape, 50, 50, base_size, color=color)
            distractors.append(create_shape_svg([shape]))

        explanation = "The colors follow a specific sequence. Identify the pattern and find the next color."

    elif pattern_type == 'shape_cycle':
        shape_sequence = random.sample(shape_types, 4)
        for shape_type in shape_sequence:
            shape = Shape(shape_type, 50, 50, base_size, color=base_color)
            sequence_images.append(create_shape_svg([shape]))

        # Distractors: wrong shapes
        remaining_shapes = [s for s in shape_types if s not in shape_sequence]
        distractors = []
        for shape_type in remaining_shapes[:3]:
            shape = Shape(shape_type, 50, 50, base_size, color=base_color)
            distractors.append(create_shape_svg([shape]))

        explanation = "The shapes follow a specific sequence. Identify the pattern and find the next shape."

    else:  # size_change
        size_step = random.choice([8, 10, 12])
        direction = random.choice([1, -1])
        start_size = 50 if direction == -1 else 20

        for i in range(4):
            size = start_size + direction * i * size_step
            shape = Shape(base_shape, 50, 50, size, color=base_color)
            sequence_images.append(create_shape_svg([shape]))

        # Distractors: wrong sizes
        correct_size = start_size + direction * 3 * size_step
        wrong_sizes = [correct_size + 10, correct_size - 10, start_size]
        distractors = []
        for size in wrong_sizes:
            shape = Shape(base_shape, 50, 50, max(15, size), color=base_color)
            distractors.append(create_shape_svg([shape]))

        explanation = f"The shape {'grows' if direction == 1 else 'shrinks'} by {size_step} units each step."

    # Build options (correct answer + distractors, shuffled)
    correct_answer_svg = sequence_images[3]
    options_svgs = [correct_answer_svg] + distractors[:3]
    random.shuffle(options_svgs)
    correct_index = options_svgs.index(correct_answer_svg)

    return {
        "question_type": "nvr_sequences",
        "text": "Look at the sequence of shapes. Which shape comes next?",
        "sequence_images": [svg_to_data_url(svg) for svg in sequence_images[:3]],
        "options": [svg_to_data_url(svg) for svg in options_svgs],
        "correct_index": correct_index,
        "explanation": explanation,
        "difficulty": 2 if pattern_type in ['rotation', 'size_change'] else 3,
    }


def generate_odd_one_out_question() -> dict:
    """Generate an odd one out question.

    4-5 shapes where one is different from the others.
    """
    shape_types = ['circle', 'square', 'triangle', 'pentagon', 'hexagon']

    # Choose what makes one different
    difference_type = random.choice(['shape', 'color', 'size', 'rotation', 'fill'])

    base_shape = random.choice(shape_types)
    base_color = random.choice(COLORS)
    base_size = 40
    base_rotation = random.choice([0, 45, 90])
    base_fill = 'solid'

    num_items = random.choice([4, 5])
    odd_index = random.randint(0, num_items - 1)

    images = []
    for i in range(num_items):
        if i == odd_index:
            # Make this one different
            if difference_type == 'shape':
                other_shapes = [s for s in shape_types if s != base_shape]
                odd_shape = random.choice(other_shapes)
                shape = Shape(odd_shape, 50, 50, base_size, base_rotation, base_color, base_fill)
            elif difference_type == 'color':
                other_colors = [c for c in COLORS if c != base_color]
                odd_color = random.choice(other_colors)
                shape = Shape(base_shape, 50, 50, base_size, base_rotation, odd_color, base_fill)
            elif difference_type == 'size':
                odd_size = base_size + random.choice([-15, 20])
                shape = Shape(base_shape, 50, 50, odd_size, base_rotation, base_color, base_fill)
            elif difference_type == 'rotation':
                odd_rotation = base_rotation + random.choice([45, 90, 180])
                shape = Shape(base_shape, 50, 50, base_size, odd_rotation, base_color, base_fill)
            else:  # fill
                odd_fill = random.choice([f for f in FILL_PATTERNS if f != base_fill])
                shape = Shape(base_shape, 50, 50, base_size, base_rotation, base_color, odd_fill)
        else:
            shape = Shape(base_shape, 50, 50, base_size, base_rotation, base_color, base_fill)

        images.append(create_shape_svg([shape]))

    explanations = {
        'shape': "The odd one out is a different shape type from the others.",
        'color': "The odd one out has a different color from the others.",
        'size': "The odd one out is a different size from the others.",
        'rotation': "The odd one out is rotated differently from the others.",
        'fill': "The odd one out has a different fill pattern from the others.",
    }

    return {
        "question_type": "nvr_odd_one_out",
        "text": "Which shape is the odd one out?",
        "images": [svg_to_data_url(svg) for svg in images],
        "correct_index": odd_index,
        "explanation": explanations[difference_type],
        "difficulty": 2,
    }


def generate_analogy_question() -> dict:
    """Generate an analogy question: A is to B as C is to ?

    The transformation from A to B should match C to answer.
    """
    shape_types = ['circle', 'square', 'triangle', 'pentagon', 'hexagon', 'star']

    # Choose transformation type
    transform_type = random.choice(['rotation', 'color_change', 'size_change', 'fill_change'])

    shape_a = random.choice(shape_types)
    shape_c = random.choice([s for s in shape_types if s != shape_a])

    color_a = random.choice(COLORS)
    size = 40

    if transform_type == 'rotation':
        rotation_amount = random.choice([90, 180, 45])
        a_shape = Shape(shape_a, 50, 50, size, rotation=0, color=color_a)
        b_shape = Shape(shape_a, 50, 50, size, rotation=rotation_amount, color=color_a)
        c_shape = Shape(shape_c, 50, 50, size, rotation=0, color=color_a)
        answer_shape = Shape(shape_c, 50, 50, size, rotation=rotation_amount, color=color_a)

        # Distractors
        distractors = [
            Shape(shape_c, 50, 50, size, rotation=rotation_amount + 90, color=color_a),
            Shape(shape_c, 50, 50, size, rotation=0, color=color_a),
            Shape(shape_a, 50, 50, size, rotation=rotation_amount, color=color_a),
        ]
        explanation = f"The first shape is rotated {rotation_amount} degrees. Apply the same rotation to the third shape."

    elif transform_type == 'color_change':
        color_b = random.choice([c for c in COLORS if c != color_a])
        a_shape = Shape(shape_a, 50, 50, size, color=color_a)
        b_shape = Shape(shape_a, 50, 50, size, color=color_b)
        c_shape = Shape(shape_c, 50, 50, size, color=color_a)
        answer_shape = Shape(shape_c, 50, 50, size, color=color_b)

        other_colors = [c for c in COLORS if c not in [color_a, color_b]]
        distractors = [
            Shape(shape_c, 50, 50, size, color=other_colors[0]),
            Shape(shape_c, 50, 50, size, color=color_a),
            Shape(shape_a, 50, 50, size, color=color_b),
        ]
        explanation = "The color changes from the first to second shape. Apply the same color change to the third shape."

    elif transform_type == 'size_change':
        size_b = size + random.choice([15, -15])
        a_shape = Shape(shape_a, 50, 50, size, color=color_a)
        b_shape = Shape(shape_a, 50, 50, size_b, color=color_a)
        c_shape = Shape(shape_c, 50, 50, size, color=color_a)
        answer_shape = Shape(shape_c, 50, 50, size_b, color=color_a)

        distractors = [
            Shape(shape_c, 50, 50, size, color=color_a),
            Shape(shape_c, 50, 50, size + 25, color=color_a),
            Shape(shape_a, 50, 50, size_b, color=color_a),
        ]
        direction = "larger" if size_b > size else "smaller"
        explanation = f"The shape becomes {direction}. Apply the same size change to the third shape."

    else:  # fill_change
        a_shape = Shape(shape_a, 50, 50, size, color=color_a, fill_pattern='solid')
        b_shape = Shape(shape_a, 50, 50, size, color=color_a, fill_pattern='empty')
        c_shape = Shape(shape_c, 50, 50, size, color=color_a, fill_pattern='solid')
        answer_shape = Shape(shape_c, 50, 50, size, color=color_a, fill_pattern='empty')

        distractors = [
            Shape(shape_c, 50, 50, size, color=color_a, fill_pattern='solid'),
            Shape(shape_c, 50, 50, size, color=color_a, fill_pattern='striped'),
            Shape(shape_a, 50, 50, size, color=color_a, fill_pattern='empty'),
        ]
        explanation = "The fill changes from solid to empty. Apply the same change to the third shape."

    # Create SVGs
    a_svg = create_shape_svg([a_shape])
    b_svg = create_shape_svg([b_shape])
    c_svg = create_shape_svg([c_shape])
    answer_svg = create_shape_svg([answer_shape])
    distractor_svgs = [create_shape_svg([d]) for d in distractors]

    # Build options
    options_svgs = [answer_svg] + distractor_svgs
    random.shuffle(options_svgs)
    correct_index = options_svgs.index(answer_svg)

    return {
        "question_type": "nvr_analogies",
        "text": "A is to B as C is to ?",
        "pair_a": [svg_to_data_url(a_svg), svg_to_data_url(b_svg)],
        "shape_c": svg_to_data_url(c_svg),
        "options": [svg_to_data_url(svg) for svg in options_svgs],
        "correct_index": correct_index,
        "explanation": explanation,
        "difficulty": 3,
    }


def generate_rotation_question() -> dict:
    """Generate a rotation identification question.

    Given a shape, identify which option shows it rotated by a specific amount.
    """
    shape_types = ['triangle', 'pentagon', 'star', 'arrow', 'diamond']

    base_shape = random.choice(shape_types)
    base_color = random.choice(COLORS)
    size = 45

    # Create original shape with some initial rotation
    initial_rotation = random.choice([0, 15, 30])
    rotation_amount = random.choice([90, 180, 270])

    original = Shape(base_shape, 50, 50, size, rotation=initial_rotation, color=base_color)
    rotated = Shape(base_shape, 50, 50, size, rotation=initial_rotation + rotation_amount, color=base_color)

    # Distractors (wrong rotations)
    wrong_rotations = [45, 135, 225, 315]
    wrong_rotations = [r for r in wrong_rotations if r != rotation_amount][:3]
    distractors = [
        Shape(base_shape, 50, 50, size, rotation=initial_rotation + r, color=base_color)
        for r in wrong_rotations
    ]

    original_svg = create_shape_svg([original])
    answer_svg = create_shape_svg([rotated])
    distractor_svgs = [create_shape_svg([d]) for d in distractors]

    options_svgs = [answer_svg] + distractor_svgs
    random.shuffle(options_svgs)
    correct_index = options_svgs.index(answer_svg)

    return {
        "question_type": "nvr_rotation",
        "text": f"Which shape shows the original rotated {rotation_amount} degrees clockwise?",
        "original_image": svg_to_data_url(original_svg),
        "options": [svg_to_data_url(svg) for svg in options_svgs],
        "correct_index": correct_index,
        "explanation": f"Rotating the shape {rotation_amount} degrees clockwise gives the correct answer.",
        "difficulty": 2,
    }


def generate_reflection_question() -> dict:
    """Generate a reflection/mirror question.

    Given a shape, identify its reflection across a vertical or horizontal axis.
    """
    # Use asymmetric shapes for meaningful reflections
    shape_types = ['triangle', 'arrow', 'star']

    base_shape = random.choice(shape_types)
    base_color = random.choice(COLORS)
    size = 45

    # Create original with some rotation to make it asymmetric
    initial_rotation = random.choice([30, 45, 60])
    axis = random.choice(['vertical', 'horizontal'])

    original = Shape(base_shape, 50, 50, size, rotation=initial_rotation, color=base_color)

    # For reflection, we flip the rotation
    if axis == 'vertical':
        reflected_rotation = -initial_rotation
    else:
        reflected_rotation = 180 - initial_rotation

    reflected = Shape(base_shape, 50, 50, size, rotation=reflected_rotation, color=base_color)

    # Distractors
    wrong_rotations = [initial_rotation + 90, initial_rotation + 180, initial_rotation]
    distractors = [
        Shape(base_shape, 50, 50, size, rotation=r, color=base_color)
        for r in wrong_rotations
    ]

    original_svg = create_shape_svg([original])
    answer_svg = create_shape_svg([reflected])
    distractor_svgs = [create_shape_svg([d]) for d in distractors]

    options_svgs = [answer_svg] + distractor_svgs
    random.shuffle(options_svgs)
    correct_index = options_svgs.index(answer_svg)

    return {
        "question_type": "nvr_reflection",
        "text": f"Which shape shows the reflection across the {axis} axis?",
        "original_image": svg_to_data_url(original_svg),
        "axis": axis,
        "options": [svg_to_data_url(svg) for svg in options_svgs],
        "correct_index": correct_index,
        "explanation": f"Reflecting across the {axis} axis flips the shape horizontally or vertically.",
        "difficulty": 3,
    }


# Convert to database format

def convert_to_db_format(question_data: dict) -> dict:
    """Convert generated question to database format."""
    qtype = question_data["question_type"]

    # Build content based on question type
    # IMPORTANT: Store the actual option value as answer, not the index
    # This is because options get shuffled on load, making index-based answers invalid
    if qtype == "nvr_sequences":
        content = {
            "text": question_data["text"],
            "images": question_data["sequence_images"],
            "options": question_data["options"],
        }
        # Store actual option value (SVG data URL)
        answer_value = question_data["options"][question_data["correct_index"]]

    elif qtype == "nvr_odd_one_out":
        # Use images as options for visual selection
        content = {
            "text": question_data["text"],
            "options": question_data["images"],  # Images ARE the options
        }
        # Store actual image as answer value
        answer_value = question_data["images"][question_data["correct_index"]]

    elif qtype == "nvr_analogies":
        content = {
            "text": question_data["text"],
            "pair_a": question_data["pair_a"],
            "shape_c": question_data["shape_c"],
            "options": question_data["options"],
        }
        # Store actual option value (SVG data URL)
        answer_value = question_data["options"][question_data["correct_index"]]

    elif qtype in ["nvr_rotation", "nvr_reflection"]:
        content = {
            "text": question_data["text"],
            "image_url": question_data["original_image"],
            "options": question_data["options"],
        }
        # Store actual option value (SVG data URL)
        answer_value = question_data["options"][question_data["correct_index"]]

    else:
        content = {"text": question_data["text"]}
        answer_value = str(question_data.get("correct_index", 0))

    return {
        "id": str(uuid.uuid4()),
        "subject": "non_verbal_reasoning",
        "question_type": qtype,
        "format": "multiple_choice",
        "difficulty": question_data.get("difficulty", 3),
        "content": content,
        "answer": {
            "value": answer_value,
            "accept_variations": None,
            "case_sensitive": False,
            "order_matters": True,
        },
        "explanation": question_data.get("explanation", ""),
        "hints": [
            {"level": 1, "text": "Look carefully at each shape's properties.", "penalty": 0.1},
            {"level": 2, "text": "Consider rotation, size, color, and fill patterns.", "penalty": 0.2},
        ],
        "tags": [qtype.replace("nvr_", ""), "shapes", "visual"],
        "source": "generated_nvr",
        "created_at": datetime.utcnow().isoformat(),
    }


# Generator registry
GENERATORS: dict[str, Callable] = {
    "nvr_sequences": generate_sequence_question,
    "nvr_odd_one_out": generate_odd_one_out_question,
    "nvr_analogies": generate_analogy_question,
    "nvr_rotation": generate_rotation_question,
    "nvr_reflection": generate_reflection_question,
}


def generate_questions(question_type: str | None, count: int) -> list[dict]:
    """Generate NVR questions."""
    questions = []

    if question_type:
        if question_type not in GENERATORS:
            print(f"Unknown question type: {question_type}")
            print(f"Available types: {list(GENERATORS.keys())}")
            return []
        generators = [GENERATORS[question_type]]
    else:
        generators = list(GENERATORS.values())

    questions_per_type = count // len(generators)
    remainder = count % len(generators)

    for i, gen in enumerate(generators):
        n = questions_per_type + (1 if i < remainder else 0)
        for _ in range(n):
            q_data = gen()
            db_format = convert_to_db_format(q_data)
            questions.append(db_format)

    return questions


def save_to_database(questions: list[dict], dry_run: bool = False):
    """Save questions to database."""
    if dry_run:
        print(f"\n[DRY RUN] Would save {len(questions)} questions")
        return

    db_path = Path(__file__).parent.parent / "data" / "tutor.db"
    conn = sqlite3.connect(db_path)
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
            pass

    conn.commit()
    conn.close()
    print(f"Saved {inserted} questions to database")


def preview_questions():
    """Generate sample questions and display in browser."""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>NVR Question Preview</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        .question { border: 1px solid #ddd; padding: 20px; margin: 20px 0; border-radius: 8px; }
        .question h3 { margin-top: 0; color: #333; }
        .images { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
        .images img { border: 1px solid #eee; border-radius: 4px; }
        .options { display: flex; gap: 10px; margin-top: 15px; }
        .options img { border: 2px solid #ddd; border-radius: 4px; cursor: pointer; }
        .options img:hover { border-color: #3B82F6; }
        .answer { margin-top: 10px; padding: 10px; background: #f0f9ff; border-radius: 4px; }
        .arrow { font-size: 24px; color: #666; }
    </style>
</head>
<body>
    <h1>Non-Verbal Reasoning Questions Preview</h1>
"""

    for name, gen in GENERATORS.items():
        q = gen()
        html += f'<div class="question">\n'
        html += f'<h3>{name.replace("_", " ").title()}</h3>\n'
        html += f'<p><strong>{q["text"]}</strong></p>\n'

        if name == "nvr_sequences":
            html += '<div class="images">\n'
            for i, img in enumerate(q["sequence_images"]):
                html += f'<img src="{img}" width="80" height="80">\n'
                if i < len(q["sequence_images"]) - 1:
                    html += '<span class="arrow">→</span>\n'
            html += '<span class="arrow">→ ?</span>\n'
            html += '</div>\n'

        elif name == "nvr_odd_one_out":
            html += '<div class="images">\n'
            for i, img in enumerate(q["images"]):
                html += f'<div style="text-align:center"><img src="{img}" width="80" height="80"><br>{i+1}</div>\n'
            html += '</div>\n'

        elif name == "nvr_analogies":
            html += '<div class="images">\n'
            html += f'<img src="{q["pair_a"][0]}" width="80" height="80">\n'
            html += '<span class="arrow">→</span>\n'
            html += f'<img src="{q["pair_a"][1]}" width="80" height="80">\n'
            html += '<span class="arrow" style="margin: 0 20px;">::</span>\n'
            html += f'<img src="{q["shape_c"]}" width="80" height="80">\n'
            html += '<span class="arrow">→ ?</span>\n'
            html += '</div>\n'

        elif name in ["nvr_rotation", "nvr_reflection"]:
            html += '<div class="images">\n'
            html += f'<div style="text-align:center"><strong>Original:</strong><br><img src="{q["original_image"]}" width="100" height="100"></div>\n'
            html += '</div>\n'

        if "options" in q:
            html += '<p><strong>Options:</strong></p>\n'
            html += '<div class="options">\n'
            for i, opt in enumerate(q["options"]):
                marker = " ✓" if i == q["correct_index"] else ""
                border = "3px solid #22C55E" if i == q["correct_index"] else "2px solid #ddd"
                html += f'<div style="text-align:center"><img src="{opt}" width="80" height="80" style="border:{border}"><br>{chr(65+i)}{marker}</div>\n'
            html += '</div>\n'

        html += f'<div class="answer"><strong>Explanation:</strong> {q["explanation"]}</div>\n'
        html += '</div>\n'

    html += '</body></html>'

    # Save and open
    preview_path = Path("/tmp/nvr_preview.html")
    preview_path.write_text(html)
    print(f"Preview saved to: {preview_path}")

    import webbrowser
    webbrowser.open(f"file://{preview_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate NVR questions with shapes")
    parser.add_argument("--type", choices=list(GENERATORS.keys()), help="Question type")
    parser.add_argument("--count", type=int, default=10, help="Number of questions")
    parser.add_argument("--all", action="store_true", help="Generate all types")
    parser.add_argument("--dry-run", action="store_true", help="Don't save to database")
    parser.add_argument("--preview", action="store_true", help="Preview in browser")

    args = parser.parse_args()

    if args.preview:
        preview_questions()
        return

    if not args.type and not args.all:
        print("Specify --type or --all, or use --preview to see samples")
        return

    qtype = args.type if not args.all else None
    questions = generate_questions(qtype, args.count)

    print(f"Generated {len(questions)} questions")

    # Show sample
    if questions:
        q = questions[0]
        print(f"\nSample: {q['question_type']}")
        print(f"  Text: {q['content']['text']}")
        print(f"  Difficulty: {q['difficulty']}")

    save_to_database(questions, args.dry_run)


if __name__ == "__main__":
    main()
