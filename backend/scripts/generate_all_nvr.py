#!/usr/bin/env python3
"""Generate all NVR (Non-Verbal Reasoning) question types.

Supports 8 question types:
- nvr_matrices: Raven's Progressive Matrices (already exists, imported)
- nvr_sequences: Pattern continuation
- nvr_odd_one_out: Find the different item
- nvr_analogies: A is to B as C is to ?
- nvr_rotation: Rotation identification
- nvr_reflection: Mirror image problems
- nvr_spatial_3d: 3D spatial reasoning (cube unfolding)
- nvr_codes: Code-breaking problems

Usage:
    uv run python scripts/generate_all_nvr.py --all --count 50
    uv run python scripts/generate_all_nvr.py --type sequences --count 30
    uv run python scripts/generate_all_nvr.py --preview sequences
"""

import argparse
import base64
import io
import json
import math
import random
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFont


# =============================================================================
# SHAPE DRAWING FUNCTIONS
# =============================================================================

def draw_circle(draw: ImageDraw, x: int, y: int, size: int, fill: str, outline: str, width: int = 2):
    """Draw a circle centered at (x, y)."""
    draw.ellipse(
        [x - size // 2, y - size // 2, x + size // 2, y + size // 2],
        fill=fill, outline=outline, width=width
    )


def draw_square(draw: ImageDraw, x: int, y: int, size: int, fill: str, outline: str, width: int = 2):
    """Draw a square centered at (x, y)."""
    draw.rectangle(
        [x - size // 2, y - size // 2, x + size // 2, y + size // 2],
        fill=fill, outline=outline, width=width
    )


def draw_triangle(draw: ImageDraw, x: int, y: int, size: int, fill: str, outline: str, width: int = 2):
    """Draw an upward-pointing triangle centered at (x, y)."""
    points = [
        (x, y - size // 2),
        (x - size // 2, y + size // 2),
        (x + size // 2, y + size // 2)
    ]
    draw.polygon(points, fill=fill, outline=outline, width=width)


def draw_diamond(draw: ImageDraw, x: int, y: int, size: int, fill: str, outline: str, width: int = 2):
    """Draw a diamond centered at (x, y)."""
    points = [
        (x, y - size // 2),
        (x + size // 2, y),
        (x, y + size // 2),
        (x - size // 2, y)
    ]
    draw.polygon(points, fill=fill, outline=outline, width=width)


def draw_pentagon(draw: ImageDraw, x: int, y: int, size: int, fill: str, outline: str, width: int = 2):
    """Draw a pentagon centered at (x, y)."""
    points = []
    for i in range(5):
        angle = math.radians(i * 72 - 90)
        px = x + int(size // 2 * math.cos(angle))
        py = y + int(size // 2 * math.sin(angle))
        points.append((px, py))
    draw.polygon(points, fill=fill, outline=outline, width=width)


def draw_hexagon(draw: ImageDraw, x: int, y: int, size: int, fill: str, outline: str, width: int = 2):
    """Draw a hexagon centered at (x, y)."""
    points = []
    for i in range(6):
        angle = math.radians(i * 60 - 90)
        px = x + int(size // 2 * math.cos(angle))
        py = y + int(size // 2 * math.sin(angle))
        points.append((px, py))
    draw.polygon(points, fill=fill, outline=outline, width=width)


def draw_cross(draw: ImageDraw, x: int, y: int, size: int, fill: str, outline: str, width: int = 2):
    """Draw a cross/plus centered at (x, y)."""
    arm_width = size // 4
    # Vertical bar
    draw.rectangle(
        [x - arm_width // 2, y - size // 2, x + arm_width // 2, y + size // 2],
        fill=fill, outline=outline, width=width
    )
    # Horizontal bar
    draw.rectangle(
        [x - size // 2, y - arm_width // 2, x + size // 2, y + arm_width // 2],
        fill=fill, outline=outline, width=width
    )


def draw_star(draw: ImageDraw, x: int, y: int, size: int, fill: str, outline: str, width: int = 2):
    """Draw a 5-pointed star centered at (x, y)."""
    outer_r = size // 2
    inner_r = size // 4
    points = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        r = outer_r if i % 2 == 0 else inner_r
        px = x + int(r * math.cos(angle))
        py = y + int(r * math.sin(angle))
        points.append((px, py))
    draw.polygon(points, fill=fill, outline=outline, width=width)


def draw_arrow(draw: ImageDraw, x: int, y: int, size: int, fill: str, outline: str, width: int = 2):
    """Draw an upward-pointing arrow centered at (x, y)."""
    # Arrow head
    head_points = [
        (x, y - size // 2),
        (x - size // 3, y),
        (x + size // 3, y)
    ]
    draw.polygon(head_points, fill=fill, outline=outline, width=width)
    # Arrow shaft
    shaft_width = size // 6
    draw.rectangle(
        [x - shaft_width, y, x + shaft_width, y + size // 2],
        fill=fill, outline=outline, width=width
    )


def draw_heart(draw: ImageDraw, x: int, y: int, size: int, fill: str, outline: str, width: int = 2):
    """Draw a heart centered at (x, y)."""
    # Approximate heart shape using curves
    r = size // 4
    # Left bump
    draw.ellipse([x - size // 2, y - size // 4, x, y + size // 4], fill=fill, outline=outline, width=width)
    # Right bump
    draw.ellipse([x, y - size // 4, x + size // 2, y + size // 4], fill=fill, outline=outline, width=width)
    # Bottom triangle
    points = [
        (x - size // 2 + r // 2, y + r // 2),
        (x, y + size // 2),
        (x + size // 2 - r // 2, y + r // 2)
    ]
    draw.polygon(points, fill=fill, outline=outline, width=width)


def draw_letter_l(draw: ImageDraw, x: int, y: int, size: int, fill: str, outline: str, width: int = 2):
    """Draw an L-shape centered at (x, y)."""
    thickness = size // 4
    # Vertical part
    draw.rectangle(
        [x - size // 2, y - size // 2, x - size // 2 + thickness, y + size // 2],
        fill=fill, outline=outline, width=width
    )
    # Horizontal part
    draw.rectangle(
        [x - size // 2, y + size // 2 - thickness, x + size // 2, y + size // 2],
        fill=fill, outline=outline, width=width
    )


SHAPES = {
    'circle': draw_circle,
    'square': draw_square,
    'triangle': draw_triangle,
    'diamond': draw_diamond,
    'pentagon': draw_pentagon,
    'hexagon': draw_hexagon,
    'cross': draw_cross,
    'star': draw_star,
    'arrow': draw_arrow,
    'letter_l': draw_letter_l,
}

# Subset of shapes that look good when rotated
ROTATABLE_SHAPES = ['triangle', 'arrow', 'letter_l', 'diamond', 'pentagon', 'star']

# Truly asymmetric shapes for rotation questions (no rotational symmetry)
# These look clearly different at each rotation angle
ASYMMETRIC_SHAPES = ['arrow', 'letter_l', 'triangle']

# Subset of shapes that look noticeably different when reflected
REFLECTABLE_SHAPES = ['letter_l', 'arrow', 'pentagon']

COLORS = ['black', 'gray', 'white']
FILL_COLORS = ['black', 'gray', None]  # None = outline only
SIZES = [25, 35, 45]


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_font(size: int = 30) -> ImageFont:
    """Get a font, falling back to default if system fonts unavailable."""
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except (OSError, IOError):
        return ImageFont.load_default()


def image_to_data_url(img: Image.Image) -> str:
    """Convert PIL Image to base64 data URL."""
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    encoded = base64.b64encode(buffer.read()).decode()
    return f"data:image/png;base64,{encoded}"


def create_cell_image(size: int = 80, bg_color: str = 'white') -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Create a blank cell image with border."""
    img = Image.new('RGB', (size, size), color=bg_color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, size - 1, size - 1], outline='black', width=1)
    return img, draw


def draw_shape_on_image(
    img: Image.Image,
    shape: str,
    x: int,
    y: int,
    size: int,
    fill: str | None,
    outline: str = 'black',
    rotation: int = 0
) -> Image.Image:
    """Draw a shape on an image, optionally rotated."""
    if rotation != 0:
        # Draw on a transparent layer, rotate, then composite
        layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        layer_draw = ImageDraw.Draw(layer)

        fill_color = fill if fill else None
        SHAPES[shape](layer_draw, x, y, size, fill_color, outline)

        # Rotate around the shape center
        rotated = layer.rotate(-rotation, center=(x, y), resample=Image.BICUBIC)

        # Convert img to RGBA if needed
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        img = Image.alpha_composite(img, rotated)
        return img.convert('RGB')
    else:
        draw = ImageDraw.Draw(img)
        fill_color = fill if fill else None
        SHAPES[shape](draw, x, y, size, fill_color, outline)
        return img


def create_composite_shape_image(
    shapes_data: list[dict],
    cell_size: int = 80,
    bg_color: str = 'white'
) -> Image.Image:
    """Create an image with multiple shapes.

    shapes_data: list of dicts with keys: shape, x, y, size, fill, rotation
    """
    img = Image.new('RGBA', (cell_size, cell_size), bg_color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, cell_size - 1, cell_size - 1], outline='black', width=1)

    for s in shapes_data:
        shape = s['shape']
        x = s.get('x', cell_size // 2)
        y = s.get('y', cell_size // 2)
        size = s.get('size', 35)
        fill = s.get('fill', 'black')
        rotation = s.get('rotation', 0)

        img = draw_shape_on_image(img, shape, x, y, size, fill, 'black', rotation)

    return img.convert('RGB')


# =============================================================================
# SEQUENCE GENERATOR (nvr_sequences)
# =============================================================================

@dataclass
class SequencePattern:
    """Defines a pattern for sequence questions."""
    name: str
    description: str


def generate_sequence_question(difficulty: int = 2) -> dict:
    """Generate a sequence question: "What comes next?"

    Pattern types:
    - Rotation progression: shape rotates by fixed amount
    - Size progression: shape grows/shrinks
    - Fill progression: fill changes (outline -> gray -> black)
    - Shape cycle: shapes cycle through a set
    - Count progression: number of shapes increases
    """
    pattern_type = random.choice([
        'rotation', 'size', 'fill', 'shape_cycle', 'count'
    ])

    sequence_length = 4  # Show 4, ask for 5th
    cell_size = 80

    if pattern_type == 'rotation':
        shape = random.choice(ROTATABLE_SHAPES)
        fill = random.choice(['black', 'gray'])
        rotation_step = random.choice([45, 90, 30, 60])

        sequence = []
        for i in range(sequence_length + 1):  # +1 for answer
            rotation = (i * rotation_step) % 360
            img = create_composite_shape_image([{
                'shape': shape, 'size': 40, 'fill': fill,
                'x': cell_size // 2, 'y': cell_size // 2, 'rotation': rotation
            }], cell_size)
            sequence.append(img)

        explanation = f"The {shape} rotates {rotation_step} degrees clockwise each step."

    elif pattern_type == 'size':
        shape = random.choice(list(SHAPES.keys()))
        fill = random.choice(['black', 'gray'])
        sizes = [20, 28, 36, 44, 52]  # Growing

        sequence = []
        for i in range(sequence_length + 1):
            img = create_composite_shape_image([{
                'shape': shape, 'size': sizes[i], 'fill': fill,
                'x': cell_size // 2, 'y': cell_size // 2
            }], cell_size)
            sequence.append(img)

        explanation = f"The {shape} grows larger with each step."

    elif pattern_type == 'fill':
        shape = random.choice(list(SHAPES.keys()))
        fills = [None, 'gray', 'black', None, 'gray']  # Cycling

        sequence = []
        for i in range(sequence_length + 1):
            img = create_composite_shape_image([{
                'shape': shape, 'size': 40, 'fill': fills[i],
                'x': cell_size // 2, 'y': cell_size // 2
            }], cell_size)
            sequence.append(img)

        explanation = "The fill cycles: outline, gray, black, then repeats."

    elif pattern_type == 'shape_cycle':
        shape_cycle = random.sample(list(SHAPES.keys()), 3)
        fill = random.choice(['black', 'gray'])

        sequence = []
        for i in range(sequence_length + 1):
            shape = shape_cycle[i % 3]
            img = create_composite_shape_image([{
                'shape': shape, 'size': 40, 'fill': fill,
                'x': cell_size // 2, 'y': cell_size // 2
            }], cell_size)
            sequence.append(img)

        explanation = f"The shapes cycle: {', '.join(shape_cycle)}, then repeat."

    else:  # count
        shape = random.choice(['circle', 'square', 'triangle', 'star'])
        fill = random.choice(['black', 'gray'])

        sequence = []
        for i in range(sequence_length + 1):
            count = i + 1
            shapes_data = []

            # Position shapes based on count
            if count == 1:
                positions = [(cell_size // 2, cell_size // 2)]
            elif count == 2:
                positions = [(30, cell_size // 2), (50, cell_size // 2)]
            elif count == 3:
                positions = [(40, 25), (25, 55), (55, 55)]
            elif count == 4:
                positions = [(25, 25), (55, 25), (25, 55), (55, 55)]
            else:
                positions = [(20, 20), (50, 20), (40, 40), (20, 60), (60, 60)]

            for px, py in positions[:count]:
                shapes_data.append({
                    'shape': shape, 'size': 20, 'fill': fill,
                    'x': px, 'y': py
                })

            img = create_composite_shape_image(shapes_data, cell_size)
            sequence.append(img)

        explanation = "One more shape is added each step."

    # Create sequence strip image (4 boxes in a row)
    strip_img = Image.new('RGB', (cell_size * 5, cell_size), 'white')
    for i in range(sequence_length):
        strip_img.paste(sequence[i], (i * cell_size, 0))

    # Add "?" in last position
    draw = ImageDraw.Draw(strip_img)
    draw.rectangle([4 * cell_size, 0, 5 * cell_size - 1, cell_size - 1], outline='black', width=1)
    font = get_font(40)
    draw.text((4 * cell_size + 30, 20), "?", fill='blue', font=font)

    # Answer is the 5th element
    answer_img = sequence[sequence_length]
    answer_url = image_to_data_url(answer_img)

    # Generate distractors
    distractors = generate_sequence_distractors(pattern_type, sequence, cell_size)
    distractor_urls = [image_to_data_url(d) for d in distractors]

    # Shuffle options
    options = [answer_url] + distractor_urls
    random.shuffle(options)

    return {
        "id": str(uuid.uuid4()),
        "subject": "non_verbal_reasoning",
        "question_type": "nvr_sequences",
        "format": "multiple_choice",
        "difficulty": difficulty,
        "content": {
            "text": "What comes next in the sequence?",
            "image_url": image_to_data_url(strip_img),
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
            {"level": 1, "text": "Look at how each element changes from one to the next.", "penalty": 0.1},
            {"level": 2, "text": "Is there rotation, size change, or a repeating pattern?", "penalty": 0.2},
        ],
        "tags": ["sequences", "patterns", "continuation"],
        "source": "nvr_generator",
        "created_at": datetime.utcnow().isoformat(),
    }


def generate_sequence_distractors(pattern_type: str, sequence: list, cell_size: int) -> list[Image.Image]:
    """Generate plausible wrong answers for sequence questions."""
    distractors = []

    # The answer is sequence[-1], create variations
    answer = sequence[-1]

    # Wrong rotation (extra or less rotation)
    if pattern_type == 'rotation':
        for angle in [45, -45, 90]:
            d = answer.rotate(angle, fillcolor='white')
            distractors.append(d)
    else:
        # Generic distractors: previous items, rotated versions
        if len(sequence) > 2:
            distractors.append(sequence[-2])  # Previous item
            distractors.append(sequence[-3])  # Two back

        # Rotated answer
        distractors.append(answer.rotate(90, fillcolor='white'))
        distractors.append(answer.rotate(180, fillcolor='white'))

    random.shuffle(distractors)
    return distractors[:3]


# =============================================================================
# ODD ONE OUT GENERATOR (nvr_odd_one_out)
# =============================================================================

def generate_odd_one_out_question(difficulty: int = 2) -> dict:
    """Generate an odd-one-out question.

    Shows 5 shapes, one differs in:
    - Shape type
    - Fill/color
    - Size
    - Rotation
    - Number of sides (for polygons)
    """
    difference_type = random.choice(['shape', 'fill', 'size', 'rotation', 'count'])
    cell_size = 80
    num_items = 5

    if difference_type == 'shape':
        # 4 same shapes, 1 different
        main_shape = random.choice(list(SHAPES.keys()))
        odd_shape = random.choice([s for s in SHAPES.keys() if s != main_shape])
        fill = random.choice(['black', 'gray'])

        items = []
        for i in range(num_items - 1):
            img = create_composite_shape_image([{
                'shape': main_shape, 'size': 40, 'fill': fill,
                'x': cell_size // 2, 'y': cell_size // 2
            }], cell_size)
            items.append(('normal', img))

        odd_img = create_composite_shape_image([{
            'shape': odd_shape, 'size': 40, 'fill': fill,
            'x': cell_size // 2, 'y': cell_size // 2
        }], cell_size)
        items.append(('odd', odd_img))

        explanation = f"The odd one out is the {odd_shape}. All others are {main_shape}s."

    elif difference_type == 'fill':
        shape = random.choice(list(SHAPES.keys()))
        main_fill = random.choice(['black', 'gray'])
        odd_fill = 'gray' if main_fill == 'black' else 'black'

        items = []
        for i in range(num_items - 1):
            img = create_composite_shape_image([{
                'shape': shape, 'size': 40, 'fill': main_fill,
                'x': cell_size // 2, 'y': cell_size // 2
            }], cell_size)
            items.append(('normal', img))

        odd_img = create_composite_shape_image([{
            'shape': shape, 'size': 40, 'fill': odd_fill,
            'x': cell_size // 2, 'y': cell_size // 2
        }], cell_size)
        items.append(('odd', odd_img))

        explanation = f"The odd one out has a {odd_fill} fill while others have {main_fill} fill."

    elif difference_type == 'size':
        shape = random.choice(list(SHAPES.keys()))
        fill = random.choice(['black', 'gray'])
        main_size = 40
        odd_size = random.choice([25, 55])

        items = []
        for i in range(num_items - 1):
            img = create_composite_shape_image([{
                'shape': shape, 'size': main_size, 'fill': fill,
                'x': cell_size // 2, 'y': cell_size // 2
            }], cell_size)
            items.append(('normal', img))

        odd_img = create_composite_shape_image([{
            'shape': shape, 'size': odd_size, 'fill': fill,
            'x': cell_size // 2, 'y': cell_size // 2
        }], cell_size)
        items.append(('odd', odd_img))

        size_desc = "smaller" if odd_size < main_size else "larger"
        explanation = f"The odd one out is {size_desc} than the others."

    elif difference_type == 'rotation':
        # Use asymmetric shapes so rotation is visible
        shape = random.choice(ASYMMETRIC_SHAPES)
        fill = random.choice(['black', 'gray'])
        main_rotation = 0
        odd_rotation = random.choice([45, 90, 180])

        items = []
        for i in range(num_items - 1):
            img = create_composite_shape_image([{
                'shape': shape, 'size': 40, 'fill': fill,
                'x': cell_size // 2, 'y': cell_size // 2, 'rotation': main_rotation
            }], cell_size)
            items.append(('normal', img))

        odd_img = create_composite_shape_image([{
            'shape': shape, 'size': 40, 'fill': fill,
            'x': cell_size // 2, 'y': cell_size // 2, 'rotation': odd_rotation
        }], cell_size)
        items.append(('odd', odd_img))

        explanation = f"The odd one out is rotated {odd_rotation} degrees while others are upright."

    else:  # count
        shape = random.choice(['circle', 'square', 'triangle'])
        fill = random.choice(['black', 'gray'])
        main_count = 2
        odd_count = random.choice([1, 3])

        items = []
        for i in range(num_items - 1):
            shapes_data = []
            positions = [(30, cell_size // 2), (50, cell_size // 2)]
            for px, py in positions:
                shapes_data.append({
                    'shape': shape, 'size': 22, 'fill': fill, 'x': px, 'y': py
                })
            img = create_composite_shape_image(shapes_data, cell_size)
            items.append(('normal', img))

        # Odd one - different count
        shapes_data = []
        if odd_count == 1:
            positions = [(cell_size // 2, cell_size // 2)]
        else:
            positions = [(25, 30), (55, 30), (40, 55)]
        for px, py in positions:
            shapes_data.append({
                'shape': shape, 'size': 22, 'fill': fill, 'x': px, 'y': py
            })
        odd_img = create_composite_shape_image(shapes_data, cell_size)
        items.append(('odd', odd_img))

        explanation = f"The odd one out has {odd_count} shape(s) while others have {main_count}."

    # Shuffle items
    random.shuffle(items)

    # Find the odd one's image
    odd_img = next(img for t, img in items if t == 'odd')

    # Create grid image showing all 5 with position labels
    grid_img = Image.new('RGB', (cell_size * 5, cell_size + 20), 'white')
    draw = ImageDraw.Draw(grid_img)
    font = get_font(14)

    for i, (_, img) in enumerate(items):
        grid_img.paste(img, (i * cell_size, 0))
        # Add position label below each shape
        label = chr(65 + i)  # A, B, C, D, E
        draw.text((i * cell_size + cell_size // 2 - 5, cell_size + 2), label, fill='black', font=font)

    # Options are the individual shape images
    options = [image_to_data_url(img) for _, img in items]
    answer_url = image_to_data_url(odd_img)

    return {
        "id": str(uuid.uuid4()),
        "subject": "non_verbal_reasoning",
        "question_type": "nvr_odd_one_out",
        "format": "multiple_choice",
        "difficulty": difficulty,
        "content": {
            "text": "Which shape is different from the others?",
            "image_url": image_to_data_url(grid_img),
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
            {"level": 1, "text": "Look at shape, size, fill, and orientation.", "penalty": 0.1},
            {"level": 2, "text": "Compare each item to the others systematically.", "penalty": 0.2},
        ],
        "tags": ["odd_one_out", "visual_comparison"],
        "source": "nvr_generator",
        "created_at": datetime.utcnow().isoformat(),
    }


# =============================================================================
# ANALOGIES GENERATOR (nvr_analogies)
# =============================================================================

def generate_analogy_question(difficulty: int = 2) -> dict:
    """Generate an analogy question: A is to B as C is to ?

    Transformation types:
    - Rotation: A rotates to become B
    - Size change: A grows/shrinks to B
    - Fill change: A's fill changes to B
    - Shape addition: A gains an element to become B
    """
    transformation = random.choice(['rotation', 'size', 'fill', 'add_element'])
    cell_size = 80

    if transformation == 'rotation':
        shape1 = random.choice(ROTATABLE_SHAPES)
        shape2 = random.choice([s for s in ROTATABLE_SHAPES if s != shape1])
        fill = random.choice(['black', 'gray'])
        rotation_amount = random.choice([90, 180, 45])

        # A: shape1 at 0 degrees
        a_img = create_composite_shape_image([{
            'shape': shape1, 'size': 40, 'fill': fill,
            'x': cell_size // 2, 'y': cell_size // 2, 'rotation': 0
        }], cell_size)

        # B: shape1 rotated
        b_img = create_composite_shape_image([{
            'shape': shape1, 'size': 40, 'fill': fill,
            'x': cell_size // 2, 'y': cell_size // 2, 'rotation': rotation_amount
        }], cell_size)

        # C: shape2 at 0 degrees
        c_img = create_composite_shape_image([{
            'shape': shape2, 'size': 40, 'fill': fill,
            'x': cell_size // 2, 'y': cell_size // 2, 'rotation': 0
        }], cell_size)

        # Answer: shape2 rotated same amount
        answer_img = create_composite_shape_image([{
            'shape': shape2, 'size': 40, 'fill': fill,
            'x': cell_size // 2, 'y': cell_size // 2, 'rotation': rotation_amount
        }], cell_size)

        # Distractors
        distractors = [
            create_composite_shape_image([{'shape': shape2, 'size': 40, 'fill': fill,
                'x': cell_size // 2, 'y': cell_size // 2, 'rotation': 0}], cell_size),
            create_composite_shape_image([{'shape': shape2, 'size': 40, 'fill': fill,
                'x': cell_size // 2, 'y': cell_size // 2, 'rotation': (rotation_amount + 90) % 360}], cell_size),
            create_composite_shape_image([{'shape': shape1, 'size': 40, 'fill': fill,
                'x': cell_size // 2, 'y': cell_size // 2, 'rotation': rotation_amount}], cell_size),
        ]

        explanation = f"The transformation is a {rotation_amount}-degree rotation."

    elif transformation == 'size':
        shape1 = random.choice(list(SHAPES.keys()))
        shape2 = random.choice([s for s in SHAPES.keys() if s != shape1])
        fill = random.choice(['black', 'gray'])
        size_a, size_b = 30, 50  # Growth

        a_img = create_composite_shape_image([{
            'shape': shape1, 'size': size_a, 'fill': fill,
            'x': cell_size // 2, 'y': cell_size // 2
        }], cell_size)

        b_img = create_composite_shape_image([{
            'shape': shape1, 'size': size_b, 'fill': fill,
            'x': cell_size // 2, 'y': cell_size // 2
        }], cell_size)

        c_img = create_composite_shape_image([{
            'shape': shape2, 'size': size_a, 'fill': fill,
            'x': cell_size // 2, 'y': cell_size // 2
        }], cell_size)

        answer_img = create_composite_shape_image([{
            'shape': shape2, 'size': size_b, 'fill': fill,
            'x': cell_size // 2, 'y': cell_size // 2
        }], cell_size)

        distractors = [
            create_composite_shape_image([{'shape': shape2, 'size': size_a, 'fill': fill,
                'x': cell_size // 2, 'y': cell_size // 2}], cell_size),
            create_composite_shape_image([{'shape': shape2, 'size': 25, 'fill': fill,
                'x': cell_size // 2, 'y': cell_size // 2}], cell_size),
            create_composite_shape_image([{'shape': shape1, 'size': size_b, 'fill': fill,
                'x': cell_size // 2, 'y': cell_size // 2}], cell_size),
        ]

        explanation = "The transformation is an increase in size."

    elif transformation == 'fill':
        shape1 = random.choice(list(SHAPES.keys()))
        shape2 = random.choice([s for s in SHAPES.keys() if s != shape1])
        fill_a, fill_b = None, 'black'  # Outline to filled

        a_img = create_composite_shape_image([{
            'shape': shape1, 'size': 40, 'fill': fill_a,
            'x': cell_size // 2, 'y': cell_size // 2
        }], cell_size)

        b_img = create_composite_shape_image([{
            'shape': shape1, 'size': 40, 'fill': fill_b,
            'x': cell_size // 2, 'y': cell_size // 2
        }], cell_size)

        c_img = create_composite_shape_image([{
            'shape': shape2, 'size': 40, 'fill': fill_a,
            'x': cell_size // 2, 'y': cell_size // 2
        }], cell_size)

        answer_img = create_composite_shape_image([{
            'shape': shape2, 'size': 40, 'fill': fill_b,
            'x': cell_size // 2, 'y': cell_size // 2
        }], cell_size)

        distractors = [
            create_composite_shape_image([{'shape': shape2, 'size': 40, 'fill': fill_a,
                'x': cell_size // 2, 'y': cell_size // 2}], cell_size),
            create_composite_shape_image([{'shape': shape2, 'size': 40, 'fill': 'gray',
                'x': cell_size // 2, 'y': cell_size // 2}], cell_size),
            create_composite_shape_image([{'shape': shape1, 'size': 40, 'fill': fill_b,
                'x': cell_size // 2, 'y': cell_size // 2}], cell_size),
        ]

        explanation = "The transformation is filling the outline shape with black."

    else:  # add_element
        shape1 = random.choice(list(SHAPES.keys()))
        shape2 = random.choice([s for s in SHAPES.keys() if s != shape1])
        inner_shape = random.choice(['circle', 'square'])
        fill = random.choice(['black', 'gray'])

        a_img = create_composite_shape_image([{
            'shape': shape1, 'size': 45, 'fill': None,
            'x': cell_size // 2, 'y': cell_size // 2
        }], cell_size)

        b_img = create_composite_shape_image([
            {'shape': shape1, 'size': 45, 'fill': None,
             'x': cell_size // 2, 'y': cell_size // 2},
            {'shape': inner_shape, 'size': 15, 'fill': fill,
             'x': cell_size // 2, 'y': cell_size // 2}
        ], cell_size)

        c_img = create_composite_shape_image([{
            'shape': shape2, 'size': 45, 'fill': None,
            'x': cell_size // 2, 'y': cell_size // 2
        }], cell_size)

        answer_img = create_composite_shape_image([
            {'shape': shape2, 'size': 45, 'fill': None,
             'x': cell_size // 2, 'y': cell_size // 2},
            {'shape': inner_shape, 'size': 15, 'fill': fill,
             'x': cell_size // 2, 'y': cell_size // 2}
        ], cell_size)

        other_inner = 'circle' if inner_shape == 'square' else 'square'
        distractors = [
            create_composite_shape_image([{'shape': shape2, 'size': 45, 'fill': None,
                'x': cell_size // 2, 'y': cell_size // 2}], cell_size),
            create_composite_shape_image([
                {'shape': shape2, 'size': 45, 'fill': None, 'x': cell_size // 2, 'y': cell_size // 2},
                {'shape': other_inner, 'size': 15, 'fill': fill, 'x': cell_size // 2, 'y': cell_size // 2}
            ], cell_size),
            create_composite_shape_image([
                {'shape': shape1, 'size': 45, 'fill': None, 'x': cell_size // 2, 'y': cell_size // 2},
                {'shape': inner_shape, 'size': 15, 'fill': fill, 'x': cell_size // 2, 'y': cell_size // 2}
            ], cell_size),
        ]

        explanation = f"The transformation adds a {inner_shape} inside the shape."

    # Create analogy display: A : B :: C : ?
    analogy_img = Image.new('RGB', (cell_size * 5 + 60, cell_size), 'white')

    analogy_img.paste(a_img, (0, 0))
    analogy_img.paste(b_img, (cell_size + 15, 0))
    analogy_img.paste(c_img, (2 * cell_size + 45, 0))

    # Draw "::" and "?"
    draw = ImageDraw.Draw(analogy_img)
    font = get_font(30)
    draw.text((cell_size + 2, cell_size // 2 - 15), ":", fill='black', font=font)
    draw.text((2 * cell_size + 30, cell_size // 2 - 15), "::", fill='black', font=font)

    # "?" box
    qx = 3 * cell_size + 60
    draw.rectangle([qx, 0, qx + cell_size - 1, cell_size - 1], outline='black', width=1)
    draw.text((qx + 30, 20), "?", fill='blue', font=get_font(40))

    answer_url = image_to_data_url(answer_img)
    distractor_urls = [image_to_data_url(d) for d in distractors]

    options = [answer_url] + distractor_urls
    random.shuffle(options)

    return {
        "id": str(uuid.uuid4()),
        "subject": "non_verbal_reasoning",
        "question_type": "nvr_analogies",
        "format": "multiple_choice",
        "difficulty": difficulty,
        "content": {
            "text": "A is to B as C is to ?",
            "image_url": image_to_data_url(analogy_img),
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
            {"level": 1, "text": "What changes from the first shape to the second?", "penalty": 0.1},
            {"level": 2, "text": "Apply the same change to the third shape.", "penalty": 0.2},
        ],
        "tags": ["analogies", "transformations", "visual_reasoning"],
        "source": "nvr_generator",
        "created_at": datetime.utcnow().isoformat(),
    }


# =============================================================================
# ROTATION GENERATOR (nvr_rotation)
# =============================================================================

def generate_rotation_question(difficulty: int = 2) -> dict:
    """Generate a rotation identification question.

    Shows original shape + rotation angle, user must identify the correctly rotated version.
    """
    # Use only asymmetric shapes that look clearly different when rotated
    shape = random.choice(ASYMMETRIC_SHAPES)
    fill = random.choice(['black', 'gray'])
    rotation_angle = random.choice([90, 180, 270, 45, 135])
    cell_size = 80

    # Original shape
    original_img = create_composite_shape_image([{
        'shape': shape, 'size': 45, 'fill': fill,
        'x': cell_size // 2, 'y': cell_size // 2, 'rotation': 0
    }], cell_size)

    # Correct answer
    answer_img = create_composite_shape_image([{
        'shape': shape, 'size': 45, 'fill': fill,
        'x': cell_size // 2, 'y': cell_size // 2, 'rotation': rotation_angle
    }], cell_size)

    # Distractors (wrong rotations)
    wrong_angles = [a for a in [0, 45, 90, 135, 180, 225, 270, 315] if a != rotation_angle]
    distractor_angles = random.sample(wrong_angles, 3)

    distractors = []
    for angle in distractor_angles:
        d_img = create_composite_shape_image([{
            'shape': shape, 'size': 45, 'fill': fill,
            'x': cell_size // 2, 'y': cell_size // 2, 'rotation': angle
        }], cell_size)
        distractors.append(d_img)

    # Create question image with original and rotation indicator
    question_img = Image.new('RGB', (cell_size * 2 + 20, cell_size), 'white')
    question_img.paste(original_img, (0, 0))

    # Arrow indicating rotation
    draw = ImageDraw.Draw(question_img)
    font = get_font(20)
    draw.text((cell_size + 5, cell_size // 2 - 10), f"{rotation_angle}°", fill='black', font=font)
    draw.text((cell_size + 5, cell_size // 2 + 10), "→", fill='black', font=get_font(25))

    answer_url = image_to_data_url(answer_img)
    distractor_urls = [image_to_data_url(d) for d in distractors]

    options = [answer_url] + distractor_urls
    random.shuffle(options)

    return {
        "id": str(uuid.uuid4()),
        "subject": "non_verbal_reasoning",
        "question_type": "nvr_rotation",
        "format": "multiple_choice",
        "difficulty": difficulty,
        "content": {
            "text": f"Which option shows the shape rotated {rotation_angle} degrees clockwise?",
            "image_url": image_to_data_url(question_img),
            "options": options,
        },
        "answer": {
            "value": answer_url,
            "accept_variations": None,
            "case_sensitive": False,
            "order_matters": True,
        },
        "explanation": f"The correct answer shows the shape rotated {rotation_angle} degrees clockwise from its original position.",
        "hints": [
            {"level": 1, "text": "Imagine rotating the shape in your mind.", "penalty": 0.1},
            {"level": 2, "text": "90 degrees is a quarter turn, 180 is half turn.", "penalty": 0.2},
        ],
        "tags": ["rotation", "spatial_reasoning", "mental_rotation"],
        "source": "nvr_generator",
        "created_at": datetime.utcnow().isoformat(),
    }


# =============================================================================
# REFLECTION GENERATOR (nvr_reflection)
# =============================================================================

def generate_reflection_question(difficulty: int = 2) -> dict:
    """Generate a reflection/mirror image question.

    Shows original shape and asks for horizontal or vertical reflection.
    """
    cell_size = 80

    # Create an asymmetric shape using multiple elements
    base_shape = random.choice(['letter_l', 'arrow'])
    fill = random.choice(['black', 'gray'])

    # Original image
    original_shapes = [{
        'shape': base_shape, 'size': 45, 'fill': fill,
        'x': cell_size // 2, 'y': cell_size // 2, 'rotation': 0
    }]

    # Add a small marker to make reflection more obvious
    marker_offset_x = random.choice([-15, 15])
    marker_offset_y = random.choice([-15, 15])
    original_shapes.append({
        'shape': 'circle', 'size': 10, 'fill': 'black',
        'x': cell_size // 2 + marker_offset_x,
        'y': cell_size // 2 + marker_offset_y
    })

    original_img = create_composite_shape_image(original_shapes, cell_size)

    # Reflection type
    reflection_type = random.choice(['horizontal', 'vertical'])

    if reflection_type == 'horizontal':
        # Flip left-right
        answer_img = original_img.transpose(Image.FLIP_LEFT_RIGHT)
        wrong_flip = original_img.transpose(Image.FLIP_TOP_BOTTOM)
    else:
        # Flip top-bottom
        answer_img = original_img.transpose(Image.FLIP_TOP_BOTTOM)
        wrong_flip = original_img.transpose(Image.FLIP_LEFT_RIGHT)

    # Distractors
    distractors = [
        wrong_flip,
        original_img.rotate(90, fillcolor='white'),
        original_img.rotate(180, fillcolor='white'),
    ]

    # Create question display
    question_img = Image.new('RGB', (cell_size + 100, cell_size), 'white')
    question_img.paste(original_img, (0, 0))

    draw = ImageDraw.Draw(question_img)
    font = get_font(16)

    if reflection_type == 'horizontal':
        # Draw vertical mirror line
        draw.line([(cell_size + 20, 10), (cell_size + 20, cell_size - 10)], fill='blue', width=2)
        draw.text((cell_size + 30, cell_size // 2 - 8), "Mirror", fill='blue', font=font)
    else:
        # Draw horizontal mirror line
        draw.line([(cell_size + 10, cell_size // 2), (cell_size + 90, cell_size // 2)], fill='blue', width=2)
        draw.text((cell_size + 30, cell_size // 2 + 5), "Mirror", fill='blue', font=font)

    answer_url = image_to_data_url(answer_img)
    distractor_urls = [image_to_data_url(d) for d in distractors]

    options = [answer_url] + distractor_urls
    random.shuffle(options)

    mirror_desc = "vertical line (left-right flip)" if reflection_type == 'horizontal' else "horizontal line (top-bottom flip)"

    return {
        "id": str(uuid.uuid4()),
        "subject": "non_verbal_reasoning",
        "question_type": "nvr_reflection",
        "format": "multiple_choice",
        "difficulty": difficulty,
        "content": {
            "text": f"Which option shows the shape reflected across the {mirror_desc}?",
            "image_url": image_to_data_url(question_img),
            "options": options,
        },
        "answer": {
            "value": answer_url,
            "accept_variations": None,
            "case_sensitive": False,
            "order_matters": True,
        },
        "explanation": f"The correct answer is the mirror image across a {mirror_desc}.",
        "hints": [
            {"level": 1, "text": "Imagine holding a mirror at the line.", "penalty": 0.1},
            {"level": 2, "text": "A horizontal flip swaps left and right; a vertical flip swaps top and bottom.", "penalty": 0.2},
        ],
        "tags": ["reflection", "mirror", "spatial_reasoning"],
        "source": "nvr_generator",
        "created_at": datetime.utcnow().isoformat(),
    }


# =============================================================================
# SPATIAL 3D GENERATOR (nvr_spatial_3d)
# =============================================================================

def draw_cube_face(draw: ImageDraw, x: int, y: int, size: int, symbol: str, fill: str = None):
    """Draw a cube face with a symbol."""
    draw.rectangle([x, y, x + size, y + size], fill=fill or 'white', outline='black', width=2)

    font = get_font(size // 2)
    # Center the symbol
    draw.text((x + size // 4, y + size // 4), symbol, fill='black', font=font)


def generate_cube_net(symbols: list[str], cell_size: int = 40) -> Image.Image:
    """Generate an unfolded cube net (cross pattern).

    Layout:
        [T]
    [L][F][R][B]
        [Bo]

    symbols order: [Top, Left, Front, Right, Back, Bottom]
    """
    width = cell_size * 4
    height = cell_size * 3
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)

    # Top face
    draw_cube_face(draw, cell_size, 0, cell_size, symbols[0])
    # Left face
    draw_cube_face(draw, 0, cell_size, cell_size, symbols[1])
    # Front face
    draw_cube_face(draw, cell_size, cell_size, cell_size, symbols[2])
    # Right face
    draw_cube_face(draw, cell_size * 2, cell_size, cell_size, symbols[3])
    # Back face
    draw_cube_face(draw, cell_size * 3, cell_size, cell_size, symbols[4])
    # Bottom face
    draw_cube_face(draw, cell_size, cell_size * 2, cell_size, symbols[5])

    return img


def draw_isometric_cube(symbols: dict, cell_size: int = 80) -> Image.Image:
    """Draw an isometric view of a cube showing 3 visible faces.

    symbols: dict with keys 'top', 'front', 'right' (the visible faces)
    """
    img = Image.new('RGB', (cell_size, cell_size), 'white')
    draw = ImageDraw.Draw(img)

    cx, cy = cell_size // 2, cell_size // 2
    s = cell_size // 3

    # Simplified isometric cube using polygon faces
    # Top face (parallelogram)
    top_points = [
        (cx, cy - s),
        (cx + s, cy - s // 2),
        (cx, cy),
        (cx - s, cy - s // 2)
    ]
    draw.polygon(top_points, fill='#e0e0e0', outline='black', width=2)

    # Front face (parallelogram)
    front_points = [
        (cx - s, cy - s // 2),
        (cx, cy),
        (cx, cy + s),
        (cx - s, cy + s // 2)
    ]
    draw.polygon(front_points, fill='#ffffff', outline='black', width=2)

    # Right face (parallelogram)
    right_points = [
        (cx, cy),
        (cx + s, cy - s // 2),
        (cx + s, cy + s // 2),
        (cx, cy + s)
    ]
    draw.polygon(right_points, fill='#c0c0c0', outline='black', width=2)

    # Draw symbols on faces
    font = get_font(s // 2)

    # Top symbol
    draw.text((cx - s // 4, cy - s // 2 - 5), symbols.get('top', ''), fill='black', font=font)
    # Front symbol
    draw.text((cx - s + 5, cy - s // 4 + 5), symbols.get('front', ''), fill='black', font=font)
    # Right symbol
    draw.text((cx + s // 4, cy - s // 4 + 5), symbols.get('right', ''), fill='black', font=font)

    return img


def generate_spatial_3d_question(difficulty: int = 2) -> dict:
    """Generate a 3D spatial reasoning question.

    Shows an unfolded cube net and asks which 3D view it could make.
    """
    cell_size = 80

    # Generate random symbols for cube faces
    available_symbols = ['A', 'B', 'C', 'X', 'O', '+', '*', '#']
    symbols = random.sample(available_symbols, 6)
    # [Top, Left, Front, Right, Back, Bottom]

    # Create unfolded net
    net_img = generate_cube_net(symbols, cell_size=40)

    # Determine which faces would be visible in different orientations
    # For a standard view: we see Top, Front, Right
    correct_visible = {
        'top': symbols[0],    # Top
        'front': symbols[2],  # Front
        'right': symbols[3]   # Right
    }

    answer_img = draw_isometric_cube(correct_visible, cell_size)

    # Create distractors with wrong face combinations
    distractors = []

    # Wrong 1: Swap two faces
    wrong1 = {'top': symbols[0], 'front': symbols[3], 'right': symbols[2]}
    distractors.append(draw_isometric_cube(wrong1, cell_size))

    # Wrong 2: Different face visible
    wrong2 = {'top': symbols[5], 'front': symbols[2], 'right': symbols[3]}
    distractors.append(draw_isometric_cube(wrong2, cell_size))

    # Wrong 3: Completely different arrangement
    wrong3 = {'top': symbols[1], 'front': symbols[4], 'right': symbols[0]}
    distractors.append(draw_isometric_cube(wrong3, cell_size))

    answer_url = image_to_data_url(answer_img)
    distractor_urls = [image_to_data_url(d) for d in distractors]

    options = [answer_url] + distractor_urls
    random.shuffle(options)

    return {
        "id": str(uuid.uuid4()),
        "subject": "non_verbal_reasoning",
        "question_type": "nvr_spatial_3d",
        "format": "multiple_choice",
        "difficulty": difficulty,
        "content": {
            "text": "If this net is folded into a cube, which view could you see?",
            "image_url": image_to_data_url(net_img),
            "options": options,
        },
        "answer": {
            "value": answer_url,
            "accept_variations": None,
            "case_sensitive": False,
            "order_matters": True,
        },
        "explanation": f"When folded, the top face shows '{symbols[0]}', front shows '{symbols[2]}', and right shows '{symbols[3]}'.",
        "hints": [
            {"level": 1, "text": "Imagine folding the net - which faces would be adjacent?", "penalty": 0.1},
            {"level": 2, "text": "The front face connects to the top and right in the net.", "penalty": 0.2},
        ],
        "tags": ["spatial_3d", "cube_nets", "mental_folding"],
        "source": "nvr_generator",
        "created_at": datetime.utcnow().isoformat(),
    }


# =============================================================================
# CODES GENERATOR (nvr_codes)
# =============================================================================

def generate_codes_question(difficulty: int = 2) -> dict:
    """Generate a code-breaking question.

    Shapes are assigned code letters. Given a new shape combination, find the code.
    """
    cell_size = 60

    # Select shapes and assign codes
    shapes_pool = random.sample(list(SHAPES.keys()), 4)
    codes_pool = random.sample(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'], 4)

    shape_to_code = dict(zip(shapes_pool, codes_pool))

    # Create code key examples (2 shapes per example)
    examples = []
    for i in range(3):
        # Pick 2 shapes for this example
        example_shapes = random.sample(shapes_pool, 2)
        example_code = ''.join(shape_to_code[s] for s in example_shapes)
        examples.append((example_shapes, example_code))

    # Create question: 2 shapes, find the code
    question_shapes = random.sample(shapes_pool, 2)
    correct_code = ''.join(shape_to_code[s] for s in question_shapes)

    # Create key image showing examples
    key_width = cell_size * 4
    key_height = cell_size * 3
    key_img = Image.new('RGB', (key_width, key_height), 'white')
    draw = ImageDraw.Draw(key_img)
    font = get_font(20)

    # Draw examples
    y_pos = 5
    for example_shapes, example_code in examples:
        x_pos = 5
        for shape in example_shapes:
            shape_img = create_composite_shape_image([{
                'shape': shape, 'size': 30, 'fill': 'black',
                'x': cell_size // 2, 'y': cell_size // 2
            }], cell_size)
            key_img.paste(shape_img, (x_pos, y_pos))
            x_pos += cell_size

        # Draw equals sign and code
        draw.text((x_pos + 5, y_pos + cell_size // 2 - 10), f"= {example_code}", fill='black', font=font)
        y_pos += cell_size

    # Create question image
    question_img = create_composite_shape_image([
        {'shape': question_shapes[0], 'size': 30, 'fill': 'black', 'x': 30, 'y': cell_size // 2},
        {'shape': question_shapes[1], 'size': 30, 'fill': 'black', 'x': 70, 'y': cell_size // 2}
    ], cell_size=100)

    # Add "= ?" to question
    q_draw = ImageDraw.Draw(question_img)
    q_draw.text((75, 40), "= ?", fill='blue', font=font)

    # Generate distractors
    wrong_codes = []
    for _ in range(3):
        # Swap one letter or use wrong combination
        wrong = list(correct_code)
        if random.random() < 0.5:
            # Swap order
            wrong = wrong[::-1]
        else:
            # Replace one letter
            idx = random.randint(0, len(wrong) - 1)
            other_codes = [c for c in codes_pool if c not in wrong]
            if other_codes:
                wrong[idx] = random.choice(other_codes)
        wrong_code = ''.join(wrong)
        if wrong_code != correct_code and wrong_code not in wrong_codes:
            wrong_codes.append(wrong_code)

    # Ensure we have exactly 3 distractors
    while len(wrong_codes) < 3:
        random_code = ''.join(random.sample(codes_pool, 2))
        if random_code != correct_code and random_code not in wrong_codes:
            wrong_codes.append(random_code)

    options = [correct_code] + wrong_codes[:3]
    random.shuffle(options)

    # Combine key and question into one image
    combined_width = key_width + 120
    combined_img = Image.new('RGB', (combined_width, key_height), 'white')
    combined_img.paste(key_img, (0, 0))
    combined_img.paste(question_img, (key_width + 10, key_height // 2 - 50))

    return {
        "id": str(uuid.uuid4()),
        "subject": "non_verbal_reasoning",
        "question_type": "nvr_codes",
        "format": "multiple_choice",
        "difficulty": difficulty,
        "content": {
            "text": "Using the code shown, what code represents the shapes on the right?",
            "image_url": image_to_data_url(combined_img),
            "options": options,
        },
        "answer": {
            "value": correct_code,
            "accept_variations": None,
            "case_sensitive": False,
            "order_matters": True,
        },
        "explanation": f"Each shape has a code letter. {question_shapes[0]} = {shape_to_code[question_shapes[0]]}, {question_shapes[1]} = {shape_to_code[question_shapes[1]]}, so the answer is {correct_code}.",
        "hints": [
            {"level": 1, "text": "Match each shape in the question to the examples.", "penalty": 0.1},
            {"level": 2, "text": "Find which letter each individual shape represents.", "penalty": 0.2},
        ],
        "tags": ["codes", "pattern_matching", "logic"],
        "source": "nvr_generator",
        "created_at": datetime.utcnow().isoformat(),
    }


# =============================================================================
# MAIN GENERATION FUNCTIONS
# =============================================================================

GENERATORS = {
    'sequences': generate_sequence_question,
    'odd_one_out': generate_odd_one_out_question,
    'analogies': generate_analogy_question,
    'rotation': generate_rotation_question,
    'reflection': generate_reflection_question,
    'spatial_3d': generate_spatial_3d_question,
    'codes': generate_codes_question,
}

TYPE_MAPPING = {
    'sequences': 'nvr_sequences',
    'odd_one_out': 'nvr_odd_one_out',
    'analogies': 'nvr_analogies',
    'rotation': 'nvr_rotation',
    'reflection': 'nvr_reflection',
    'spatial_3d': 'nvr_spatial_3d',
    'codes': 'nvr_codes',
}


def generate_questions(qtype: str, count: int) -> list[dict]:
    """Generate questions of a specific type."""
    if qtype not in GENERATORS:
        raise ValueError(f"Unknown question type: {qtype}")

    generator = GENERATORS[qtype]
    questions = []

    for i in range(count):
        difficulty = random.choices([1, 2, 3, 4], weights=[0.2, 0.3, 0.3, 0.2])[0]
        q = generator(difficulty)
        questions.append(q)

        if (i + 1) % 10 == 0:
            print(f"  Generated {i + 1}/{count} {qtype} questions...")

    return questions


def save_to_database(questions: list[dict], question_type: str):
    """Save questions to the database."""
    db_path = Path("data/tutor.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Delete existing questions of this type from nvr_generator
    cursor.execute(
        "DELETE FROM questions WHERE question_type = ? AND source = 'nvr_generator'",
        (question_type,)
    )
    deleted = cursor.rowcount
    if deleted:
        print(f"  Deleted {deleted} existing {question_type} questions")

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
    print(f"  Saved {len(questions)} {question_type} questions to database")

    conn.close()


def show_counts():
    """Show current NVR question counts by type."""
    db_path = Path("data/tutor.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT question_type, COUNT(*)
        FROM questions
        WHERE subject = 'non_verbal_reasoning'
        GROUP BY question_type
        ORDER BY question_type
    """)

    print("\nNVR Question Counts:")
    print("-" * 40)
    total = 0
    for qtype, count in cursor.fetchall():
        print(f"  {qtype:25} {count:5}")
        total += count
    print("-" * 40)
    print(f"  {'Total':25} {total:5}")

    conn.close()


def preview_question(qtype: str):
    """Generate and display a sample question in browser."""
    import webbrowser
    import tempfile

    if qtype not in GENERATORS:
        print(f"Unknown type: {qtype}. Available: {', '.join(GENERATORS.keys())}")
        return

    print(f"Generating sample {qtype} question...")
    q = GENERATORS[qtype](difficulty=2)

    # Check if options are images or text
    options_are_images = q['content']['options'][0].startswith('data:image')

    if options_are_images:
        options_html = ""
        for i, opt in enumerate(q['content']['options']):
            is_correct = opt == q['answer']['value']
            correct_class = 'correct' if is_correct else ''
            label = chr(65 + i)
            options_html += f"""
                <div class="option {correct_class}">
                    <img src="{opt}" alt="Option {label}">
                    <p><strong>{label}</strong>{' (Correct)' if is_correct else ''}</p>
                </div>
            """
    else:
        options_html = ""
        for i, opt in enumerate(q['content']['options']):
            is_correct = opt == q['answer']['value']
            correct_class = 'correct' if is_correct else ''
            label = chr(65 + i)
            options_html += f"""
                <div class="option text-option {correct_class}">
                    <p><strong>{label}.</strong> {opt}{' (Correct)' if is_correct else ''}</p>
                </div>
            """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>NVR Question Preview - {qtype}</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
            .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }}
            .question-image {{ margin: 20px 0; text-align: center; }}
            .question-image img {{ max-width: 100%; border: 2px solid #333; }}
            .options {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
            .option {{ border: 2px solid #ccc; padding: 10px; text-align: center; cursor: pointer; background: white; border-radius: 8px; }}
            .option:hover {{ border-color: #007bff; }}
            .option img {{ max-width: 80px; max-height: 80px; }}
            .text-option {{ text-align: left; padding: 15px; }}
            .correct {{ border-color: #28a745 !important; background: #e8f5e9; }}
            h2 {{ color: #333; margin-top: 0; }}
            .explanation {{ background: #e3f2fd; padding: 15px; border-radius: 8px; margin-top: 20px; }}
            .meta {{ color: #666; font-size: 0.9em; margin-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Type: {q['question_type']}</h2>
            <p><strong>{q['content']['text']}</strong></p>

            <div class="question-image">
                <img src="{q['content']['image_url']}" alt="Question">
            </div>

            <h3>Choose the answer:</h3>
            <div class="options">
                {options_html}
            </div>

            <div class="explanation">
                <strong>Explanation:</strong> {q['explanation']}
            </div>

            <div class="meta">
                <p>Difficulty: {q['difficulty']} | Tags: {', '.join(q['tags'])}</p>
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
    parser = argparse.ArgumentParser(description="Generate NVR questions of various types")
    parser.add_argument("--type", choices=list(GENERATORS.keys()), help="Question type to generate")
    parser.add_argument("--all", action="store_true", help="Generate all question types")
    parser.add_argument("--count", type=int, default=50, help="Number of questions per type")
    parser.add_argument("--preview", metavar="TYPE", help="Preview a sample question of given type")
    parser.add_argument("--counts", action="store_true", help="Show current question counts")

    args = parser.parse_args()

    if args.counts:
        show_counts()
        return

    if args.preview:
        preview_question(args.preview)
        return

    if args.all:
        types_to_generate = list(GENERATORS.keys())
    elif args.type:
        types_to_generate = [args.type]
    else:
        parser.print_help()
        return

    for qtype in types_to_generate:
        db_type = TYPE_MAPPING[qtype]
        print(f"\nGenerating {args.count} {qtype} questions...")
        questions = generate_questions(qtype, args.count)
        save_to_database(questions, db_type)

    show_counts()


if __name__ == "__main__":
    main()
