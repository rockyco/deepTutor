#!/usr/bin/env python3
"""Generate SVG images for NVR questions based on text descriptions.

This generator handles 8 different NVR question types with type-specific
rendering logic to correctly parse and visualize each question format.
"""

import json
import math
import os
import re
from pathlib import Path
from typing import Any

# Output directory for SVG images
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "images" / "nvr"
QUESTIONS_FILE = Path(__file__).parent.parent / "data" / "questions" / "non_verbal_reasoning.json"

# SVG dimensions
SVG_WIDTH = 120
SVG_HEIGHT = 120
OPTION_SIZE = 100


def create_svg_header(width: int = SVG_WIDTH, height: int = SVG_HEIGHT) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">'


def create_svg_footer() -> str:
    return "</svg>"


# =============================================================================
# SHAPE DRAWING PRIMITIVES
# =============================================================================

def draw_shape(shape: str, cx: float, cy: float, size: float,
               fill: str = "none", stroke: str = "#333", stroke_width: float = 2,
               rotation: float = 0) -> str:
    """Draw a basic shape centered at (cx, cy)."""

    transform = f' transform="rotate({rotation} {cx} {cy})"' if rotation else ""

    if shape == "circle":
        r = size / 2
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{transform}/>'

    elif shape in ("square", "rectangle"):
        half = size / 2
        return f'<rect x="{cx - half}" y="{cy - half}" width="{size}" height="{size}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{transform}/>'

    elif shape == "triangle":
        h = size * 0.866
        points = f"{cx},{cy - h/2} {cx - size/2},{cy + h/2} {cx + size/2},{cy + h/2}"
        return f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{transform}/>'

    elif shape == "pentagon":
        return draw_polygon(5, cx, cy, size/2, fill, stroke, stroke_width, rotation - 90)

    elif shape == "hexagon":
        return draw_polygon(6, cx, cy, size/2, fill, stroke, stroke_width, rotation)

    elif shape == "star":
        return draw_star(cx, cy, size/2, fill, stroke, stroke_width, rotation)

    elif shape == "diamond":
        half = size / 2
        points = f"{cx},{cy - half} {cx + half},{cy} {cx},{cy + half} {cx - half},{cy}"
        return f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{transform}/>'

    elif shape == "cross":
        # Plus sign shape
        arm_width = size / 3
        half = size / 2
        return f'''<path d="M {cx - arm_width/2},{cy - half}
                   h {arm_width} v {half - arm_width/2}
                   h {half - arm_width/2} v {arm_width}
                   h -{half - arm_width/2} v {half - arm_width/2}
                   h -{arm_width} v -{half - arm_width/2}
                   h -{half - arm_width/2} v -{arm_width}
                   h {half - arm_width/2} Z"
                   fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{transform}/>'''

    return ""


def draw_polygon(sides: int, cx: float, cy: float, r: float,
                 fill: str = "none", stroke: str = "#333", stroke_width: float = 2,
                 rotation: float = 0) -> str:
    """Draw a regular polygon."""
    points = []
    for i in range(sides):
        angle = (2 * math.pi * i / sides) - math.pi/2 + math.radians(rotation)
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append(f"{x:.1f},{y:.1f}")
    return f'<polygon points="{" ".join(points)}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'


def draw_star(cx: float, cy: float, r: float,
              fill: str = "none", stroke: str = "#333", stroke_width: float = 2,
              rotation: float = 0) -> str:
    """Draw a 5-pointed star."""
    points = []
    inner_r = r * 0.4
    for i in range(10):
        angle = (2 * math.pi * i / 10) - math.pi/2 + math.radians(rotation)
        radius = r if i % 2 == 0 else inner_r
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        points.append(f"{x:.1f},{y:.1f}")
    return f'<polygon points="{" ".join(points)}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'


def draw_arrow(cx: float, cy: float, direction: str, size: float = 20,
               stroke: str = "#333", stroke_width: float = 2, fill: str = None) -> str:
    """Draw an arrow pointing in a direction."""
    half = size / 2
    head_size = size / 3
    arrow_fill = fill if fill else stroke

    directions = {
        "up": (0, -1),
        "down": (0, 1),
        "left": (-1, 0),
        "right": (1, 0),
    }

    dx, dy = directions.get(direction.lower(), (0, -1))

    x1, y1 = cx - dx * half, cy - dy * half
    x2, y2 = cx + dx * half, cy + dy * half

    if direction.lower() in ["up", "down"]:
        head = f'<polygon points="{x2},{y2} {x2-head_size/2},{y2-dy*head_size} {x2+head_size/2},{y2-dy*head_size}" fill="{arrow_fill}"/>'
    else:
        head = f'<polygon points="{x2},{y2} {x2-dx*head_size},{y2-head_size/2} {x2-dx*head_size},{y2+head_size/2}" fill="{arrow_fill}"/>'

    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{stroke_width}"/>{head}'


def draw_line(x1: float, y1: float, x2: float, y2: float,
              stroke: str = "#333", stroke_width: float = 2, bold: bool = False) -> str:
    """Draw a line."""
    sw = stroke_width * 2 if bold else stroke_width
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"/>'


def draw_dot(cx: float, cy: float, r: float = 4, fill: str = "#333") -> str:
    """Draw a filled dot."""
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"/>'


def draw_dots_below(count: int, cx: float, base_y: float, spacing: float = 12) -> str:
    """Draw dots in a row below a shape."""
    dots = []
    total_width = (count - 1) * spacing
    start_x = cx - total_width / 2
    for i in range(count):
        dots.append(draw_dot(start_x + i * spacing, base_y, 3))
    return "".join(dots)


def draw_dots_inside(count: int, cx: float, cy: float, arrangement: str = "line") -> str:
    """Draw dots inside a shape."""
    dots = []
    if arrangement == "line":
        spacing = 10
        total_width = (count - 1) * spacing
        start_x = cx - total_width / 2
        for i in range(count):
            dots.append(draw_dot(start_x + i * spacing, cy, 3))
    elif arrangement == "triangle":
        if count == 3:
            dots.append(draw_dot(cx, cy - 8, 3))
            dots.append(draw_dot(cx - 8, cy + 6, 3))
            dots.append(draw_dot(cx + 8, cy + 6, 3))
    elif arrangement == "square":
        if count == 4:
            offset = 8
            dots.append(draw_dot(cx - offset, cy - offset, 3))
            dots.append(draw_dot(cx + offset, cy - offset, 3))
            dots.append(draw_dot(cx - offset, cy + offset, 3))
            dots.append(draw_dot(cx + offset, cy + offset, 3))
    elif arrangement == "diamond":
        if count == 4:
            offset = 10
            dots.append(draw_dot(cx, cy - offset, 3))
            dots.append(draw_dot(cx + offset, cy, 3))
            dots.append(draw_dot(cx, cy + offset, 3))
            dots.append(draw_dot(cx - offset, cy, 3))
    else:
        # Default grid/line arrangement
        spacing = 8
        total_width = (count - 1) * spacing
        start_x = cx - total_width / 2
        for i in range(count):
            dots.append(draw_dot(start_x + i * spacing, cy, 3))
    return "".join(dots)


def draw_corner_dots(count: int, width: int, height: int, margin: float = 12) -> str:
    """Draw dots in corners, clockwise from top-left."""
    positions = [
        (margin, margin),           # top-left
        (width - margin, margin),   # top-right
        (width - margin, height - margin),  # bottom-right
        (margin, height - margin),  # bottom-left
    ]
    dots = []
    for i in range(min(count, 4)):
        x, y = positions[i]
        dots.append(draw_dot(x, y, 3))
    return "".join(dots)


def draw_letter(letter: str, cx: float, cy: float, size: float = 30,
                rotation: float = 0, fill: str = "#333") -> str:
    """Draw a letter character."""
    transform = f' transform="rotate({rotation} {cx} {cy})"' if rotation else ""
    return f'<text x="{cx}" y="{cy + size/3}" text-anchor="middle" font-size="{size}" font-family="Arial, sans-serif" fill="{fill}"{transform}>{letter}</text>'


def draw_l_shape(cx: float, cy: float, size: float, rotation: float = 0,
                 fill: str = "none", stroke: str = "#333") -> str:
    """Draw an L-shaped figure."""
    half = size / 2
    arm = size / 3
    # L shape: vertical bar on left, horizontal at bottom
    path = f"M {cx - half},{cy - half} v {size} h {size} v -{arm} h -{size + arm - arm} v -{size - arm} Z"
    transform = f' transform="rotate({rotation} {cx} {cy})"' if rotation else ""
    return f'<path d="{path}" fill="{fill}" stroke="{stroke}" stroke-width="2"{transform}/>'


def draw_t_shape(cx: float, cy: float, size: float, rotation: float = 0,
                 fill: str = "none", stroke: str = "#333") -> str:
    """Draw a T-shaped figure."""
    arm = size / 3
    half = size / 2
    # T shape
    transform = f' transform="rotate({rotation} {cx} {cy})"' if rotation else ""
    return f'''<path d="M {cx - half},{cy - half} h {size} v {arm} h -{half + arm/2} v {size - arm} h -{arm} v -{size - arm} h -{half + arm/2} Z"
               fill="{fill}" stroke="{stroke}" stroke-width="2"{transform}/>'''


# =============================================================================
# DIVIDED SHAPES AND PATTERNS
# =============================================================================

def draw_divided_circle(cx: float, cy: float, r: float, fills: list,
                        stroke: str = "#333", stroke_width: float = 2) -> str:
    """Draw circle divided into 4 quarters with specified fills.

    fills = [top_left, top_right, bottom_right, bottom_left] or
            [left, right] for 2-part division
    """
    elements = []

    if len(fills) == 4:
        # 4 quarters using path arcs
        # Top-left quarter
        elements.append(f'<path d="M {cx},{cy} L {cx},{cy-r} A {r},{r} 0 0 0 {cx-r},{cy} Z" fill="{fills[0]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
        # Top-right quarter
        elements.append(f'<path d="M {cx},{cy} L {cx-r},{cy} A {r},{r} 0 0 0 {cx},{cy+r} Z" fill="{fills[3]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
        # Bottom-right quarter
        elements.append(f'<path d="M {cx},{cy} L {cx},{cy+r} A {r},{r} 0 0 0 {cx+r},{cy} Z" fill="{fills[2]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
        # Bottom-left quarter
        elements.append(f'<path d="M {cx},{cy} L {cx+r},{cy} A {r},{r} 0 0 0 {cx},{cy-r} Z" fill="{fills[1]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
    elif len(fills) == 2:
        # Vertical division (left/right)
        elements.append(f'<path d="M {cx},{cy-r} A {r},{r} 0 0 0 {cx},{cy+r} Z" fill="{fills[0]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
        elements.append(f'<path d="M {cx},{cy-r} A {r},{r} 0 0 1 {cx},{cy+r} Z" fill="{fills[1]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')

    # Outline
    elements.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{stroke}" stroke-width="{stroke_width}"/>')

    return "".join(elements)


def draw_divided_square(cx: float, cy: float, size: float, fills: list,
                        division: str = "vertical", stroke: str = "#333",
                        stroke_width: float = 2) -> str:
    """Draw square divided into parts with specified fills.

    division: "vertical", "horizontal", "quarters", "checkerboard"
    """
    half = size / 2
    elements = []

    if division == "vertical" and len(fills) >= 2:
        # Left half
        elements.append(f'<rect x="{cx-half}" y="{cy-half}" width="{half}" height="{size}" fill="{fills[0]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
        # Right half
        elements.append(f'<rect x="{cx}" y="{cy-half}" width="{half}" height="{size}" fill="{fills[1]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')

    elif division == "horizontal" and len(fills) >= 2:
        # Top half
        elements.append(f'<rect x="{cx-half}" y="{cy-half}" width="{size}" height="{half}" fill="{fills[0]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
        # Bottom half
        elements.append(f'<rect x="{cx-half}" y="{cy}" width="{size}" height="{half}" fill="{fills[1]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')

    elif division == "quarters" and len(fills) >= 4:
        quarter = half
        # Top-left
        elements.append(f'<rect x="{cx-half}" y="{cy-half}" width="{quarter}" height="{quarter}" fill="{fills[0]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
        # Top-right
        elements.append(f'<rect x="{cx}" y="{cy-half}" width="{quarter}" height="{quarter}" fill="{fills[1]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
        # Bottom-right
        elements.append(f'<rect x="{cx}" y="{cy}" width="{quarter}" height="{quarter}" fill="{fills[2]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
        # Bottom-left
        elements.append(f'<rect x="{cx-half}" y="{cy}" width="{quarter}" height="{quarter}" fill="{fills[3]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')

    elif division == "checkerboard":
        # 2x2 checkerboard pattern (alternating)
        quarter = half
        colors = fills if len(fills) >= 2 else ["#333", "#fff"]
        # Top-left (color 0)
        elements.append(f'<rect x="{cx-half}" y="{cy-half}" width="{quarter}" height="{quarter}" fill="{colors[0]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
        # Top-right (color 1)
        elements.append(f'<rect x="{cx}" y="{cy-half}" width="{quarter}" height="{quarter}" fill="{colors[1]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
        # Bottom-right (color 0)
        elements.append(f'<rect x="{cx}" y="{cy}" width="{quarter}" height="{quarter}" fill="{colors[0]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
        # Bottom-left (color 1)
        elements.append(f'<rect x="{cx-half}" y="{cy}" width="{quarter}" height="{quarter}" fill="{colors[1]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')

    # Outline
    elements.append(f'<rect x="{cx-half}" y="{cy-half}" width="{size}" height="{size}" fill="none" stroke="{stroke}" stroke-width="{stroke_width}"/>')

    return "".join(elements)


def draw_divided_shape(cx: float, cy: float, size: float, shape: str,
                       fills: list, division: str = "vertical",
                       stroke: str = "#333", stroke_width: float = 2) -> str:
    """Generic divided shape renderer."""
    if shape == "circle":
        return draw_divided_circle(cx, cy, size/2, fills, stroke, stroke_width)
    elif shape in ("square", "rectangle"):
        return draw_divided_square(cx, cy, size, fills, division, stroke, stroke_width)
    elif shape == "triangle":
        return draw_divided_triangle(cx, cy, size, fills, stroke, stroke_width)
    elif shape == "hexagon":
        return draw_divided_hexagon(cx, cy, size, fills, stroke, stroke_width)
    elif shape == "pentagon":
        return draw_divided_pentagon(cx, cy, size, fills, stroke, stroke_width)
    else:
        # Fallback - just draw the shape with first fill
        return draw_shape(shape, cx, cy, size, fill=fills[0] if fills else "none", stroke=stroke)


def draw_divided_triangle(cx: float, cy: float, size: float, fills: list,
                          stroke: str = "#333", stroke_width: float = 2) -> str:
    """Draw triangle divided vertically."""
    h = size * 0.866
    # Triangle points: top, bottom-left, bottom-right
    top = (cx, cy - h/2)
    bl = (cx - size/2, cy + h/2)
    br = (cx + size/2, cy + h/2)
    mid_bottom = (cx, cy + h/2)

    elements = []
    if len(fills) >= 2:
        # Left half
        elements.append(f'<polygon points="{top[0]},{top[1]} {bl[0]},{bl[1]} {mid_bottom[0]},{mid_bottom[1]}" fill="{fills[0]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
        # Right half
        elements.append(f'<polygon points="{top[0]},{top[1]} {mid_bottom[0]},{mid_bottom[1]} {br[0]},{br[1]}" fill="{fills[1]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
    # Outline
    elements.append(f'<polygon points="{top[0]},{top[1]} {bl[0]},{bl[1]} {br[0]},{br[1]}" fill="none" stroke="{stroke}" stroke-width="{stroke_width}"/>')
    return "".join(elements)


def draw_divided_hexagon(cx: float, cy: float, size: float, fills: list,
                         stroke: str = "#333", stroke_width: float = 2) -> str:
    """Draw hexagon divided vertically."""
    r = size / 2
    # Get hexagon points
    points = []
    for i in range(6):
        angle = (2 * math.pi * i / 6)
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))

    elements = []
    if len(fills) >= 2:
        # Left half (points 2, 3, 4 and center)
        left_pts = f"{cx},{cy} {points[2][0]},{points[2][1]} {points[3][0]},{points[3][1]} {points[4][0]},{points[4][1]}"
        elements.append(f'<polygon points="{left_pts}" fill="{fills[0]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
        # Right half (points 0, 1, 5 and center)
        right_pts = f"{cx},{cy} {points[0][0]},{points[0][1]} {points[1][0]},{points[1][1]} {points[5][0]},{points[5][1]}"
        elements.append(f'<polygon points="{right_pts}" fill="{fills[1]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')

    # Outline
    pts_str = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in points)
    elements.append(f'<polygon points="{pts_str}" fill="none" stroke="{stroke}" stroke-width="{stroke_width}"/>')
    return "".join(elements)


def draw_divided_pentagon(cx: float, cy: float, size: float, fills: list,
                          stroke: str = "#333", stroke_width: float = 2) -> str:
    """Draw pentagon divided vertically."""
    r = size / 2
    # Get pentagon points
    points = []
    for i in range(5):
        angle = (2 * math.pi * i / 5) - math.pi/2
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))

    elements = []
    if len(fills) >= 2:
        # Approximate vertical split
        # Left: top, bottom-left points and center
        left_pts = f"{cx},{cy} {points[0][0]},{points[0][1]} {points[3][0]},{points[3][1]} {points[4][0]},{points[4][1]}"
        elements.append(f'<polygon points="{left_pts}" fill="{fills[0]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
        # Right: remaining points and center
        right_pts = f"{cx},{cy} {points[0][0]},{points[0][1]} {points[1][0]},{points[1][1]} {points[2][0]},{points[2][1]} {points[3][0]},{points[3][1]}"
        elements.append(f'<polygon points="{right_pts}" fill="{fills[1]}" stroke="{stroke}" stroke-width="{stroke_width}"/>')

    # Outline
    pts_str = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in points)
    elements.append(f'<polygon points="{pts_str}" fill="none" stroke="{stroke}" stroke-width="{stroke_width}"/>')
    return "".join(elements)


# =============================================================================
# PATTERN FILLS
# =============================================================================

def create_stripe_pattern(pattern_id: str, direction: str = "horizontal",
                          spacing: int = 5, color: str = "#333") -> str:
    """Create SVG pattern definition for stripes."""
    if direction == "horizontal":
        return f'''<defs>
            <pattern id="{pattern_id}" patternUnits="userSpaceOnUse" width="{spacing*2}" height="{spacing*2}">
                <line x1="0" y1="0" x2="{spacing*2}" y2="0" stroke="{color}" stroke-width="1"/>
                <line x1="0" y1="{spacing}" x2="{spacing*2}" y2="{spacing}" stroke="{color}" stroke-width="1"/>
            </pattern>
        </defs>'''
    elif direction == "vertical":
        return f'''<defs>
            <pattern id="{pattern_id}" patternUnits="userSpaceOnUse" width="{spacing*2}" height="{spacing*2}">
                <line x1="0" y1="0" x2="0" y2="{spacing*2}" stroke="{color}" stroke-width="1"/>
                <line x1="{spacing}" y1="0" x2="{spacing}" y2="{spacing*2}" stroke="{color}" stroke-width="1"/>
            </pattern>
        </defs>'''
    elif direction == "diagonal" or direction == "tlbr":
        return f'''<defs>
            <pattern id="{pattern_id}" patternUnits="userSpaceOnUse" width="{spacing*2}" height="{spacing*2}" patternTransform="rotate(45)">
                <line x1="0" y1="0" x2="0" y2="{spacing*2}" stroke="{color}" stroke-width="1"/>
                <line x1="{spacing}" y1="0" x2="{spacing}" y2="{spacing*2}" stroke="{color}" stroke-width="1"/>
            </pattern>
        </defs>'''
    elif direction == "trbl":
        return f'''<defs>
            <pattern id="{pattern_id}" patternUnits="userSpaceOnUse" width="{spacing*2}" height="{spacing*2}" patternTransform="rotate(-45)">
                <line x1="0" y1="0" x2="0" y2="{spacing*2}" stroke="{color}" stroke-width="1"/>
                <line x1="{spacing}" y1="0" x2="{spacing}" y2="{spacing*2}" stroke="{color}" stroke-width="1"/>
            </pattern>
        </defs>'''
    return ""


def create_dots_pattern(pattern_id: str, spacing: int = 8, radius: int = 2,
                        color: str = "#333") -> str:
    """Create SVG pattern definition for dots."""
    return f'''<defs>
        <pattern id="{pattern_id}" patternUnits="userSpaceOnUse" width="{spacing}" height="{spacing}">
            <circle cx="{spacing/2}" cy="{spacing/2}" r="{radius}" fill="{color}"/>
        </pattern>
    </defs>'''


def create_crosshatch_pattern(pattern_id: str, spacing: int = 6,
                              color: str = "#333") -> str:
    """Create SVG pattern definition for crosshatch."""
    return f'''<defs>
        <pattern id="{pattern_id}" patternUnits="userSpaceOnUse" width="{spacing}" height="{spacing}">
            <line x1="0" y1="0" x2="{spacing}" y2="{spacing}" stroke="{color}" stroke-width="1"/>
            <line x1="{spacing}" y1="0" x2="0" y2="{spacing}" stroke="{color}" stroke-width="1"/>
        </pattern>
    </defs>'''


# =============================================================================
# SPECIAL SHAPES
# =============================================================================

def draw_flag(cx: float, cy: float, size: float, direction: str = "right",
              fill: str = "none", stroke: str = "#333", stroke_width: float = 2) -> str:
    """Draw a flag/pennant shape pointing in specified direction.

    Flag = rectangle body + triangular point
    """
    # Flag dimensions
    body_length = size * 0.6
    body_height = size * 0.5
    point_length = size * 0.4

    if direction == "right":
        # Body rectangle then triangle point
        path = f'''M {cx - size/2},{cy - body_height/2}
                   h {body_length} l {point_length},{body_height/2} l -{point_length},{body_height/2}
                   h -{body_length} Z'''
    elif direction == "left":
        path = f'''M {cx + size/2},{cy - body_height/2}
                   h -{body_length} l -{point_length},{body_height/2} l {point_length},{body_height/2}
                   h {body_length} Z'''
    elif direction == "up":
        path = f'''M {cx - body_height/2},{cy + size/2}
                   v -{body_length} l {body_height/2},-{point_length} l {body_height/2},{point_length}
                   v {body_length} Z'''
    elif direction == "down":
        path = f'''M {cx - body_height/2},{cy - size/2}
                   v {body_length} l {body_height/2},{point_length} l {body_height/2},-{point_length}
                   v -{body_length} Z'''
    else:
        # Default to right
        path = f'''M {cx - size/2},{cy - body_height/2}
                   h {body_length} l {point_length},{body_height/2} l -{point_length},{body_height/2}
                   h -{body_length} Z'''

    return f'<path d="{path}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'


def draw_semicircle(cx: float, cy: float, r: float, orientation: str = "top",
                    fill: str = "none", stroke: str = "#333",
                    stroke_width: float = 2) -> str:
    """Draw half circle - top, bottom, left, or right half."""
    if orientation == "top":
        # Top half: arc from left to right
        return f'<path d="M {cx-r},{cy} A {r},{r} 0 0 1 {cx+r},{cy} Z" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
    elif orientation == "bottom":
        # Bottom half: arc from right to left
        return f'<path d="M {cx+r},{cy} A {r},{r} 0 0 1 {cx-r},{cy} Z" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
    elif orientation == "left":
        # Left half: arc from top to bottom
        return f'<path d="M {cx},{cy-r} A {r},{r} 0 0 0 {cx},{cy+r} Z" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
    elif orientation == "right":
        # Right half: arc from bottom to top
        return f'<path d="M {cx},{cy+r} A {r},{r} 0 0 0 {cx},{cy-r} Z" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
    return ""


def draw_half_square(cx: float, cy: float, size: float, orientation: str = "left",
                     fill: str = "none", stroke: str = "#333",
                     stroke_width: float = 2) -> str:
    """Draw half of a square (rectangle with half the width or height)."""
    half = size / 2

    if orientation in ("left", "right"):
        # Half width rectangle
        if orientation == "left":
            return f'<rect x="{cx-half}" y="{cy-half}" width="{half}" height="{size}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
        else:
            return f'<rect x="{cx}" y="{cy-half}" width="{half}" height="{size}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
    elif orientation in ("top", "bottom"):
        # Half height rectangle
        if orientation == "top":
            return f'<rect x="{cx-half}" y="{cy-half}" width="{size}" height="{half}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
        else:
            return f'<rect x="{cx-half}" y="{cy}" width="{size}" height="{half}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
    return ""


def draw_quarter_square(cx: float, cy: float, size: float,
                        fill: str = "none", stroke: str = "#333",
                        stroke_width: float = 2) -> str:
    """Draw a quarter of a square (small square, 1/4 the area)."""
    quarter = size / 2
    return f'<rect x="{cx - quarter/2}" y="{cy - quarter/2}" width="{quarter}" height="{quarter}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'


def draw_half_square_triangle(cx: float, cy: float, size: float,
                              fill: str = "none", stroke: str = "#333",
                              stroke_width: float = 2) -> str:
    """Draw half a square as a right triangle (diagonal cut)."""
    half = size / 2
    # Right triangle - half of a square diagonally
    points = f"{cx - half},{cy - half} {cx + half},{cy - half} {cx + half},{cy + half}"
    return f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'


# =============================================================================
# INTERNAL PATTERNS (inside shapes)
# =============================================================================

def draw_internal_cross(cx: float, cy: float, size: float,
                        stroke: str = "#333", stroke_width: float = 2) -> str:
    """Draw a plus sign (+) pattern inside frame area."""
    half = size / 2 * 0.7
    return f'''<line x1="{cx-half}" y1="{cy}" x2="{cx+half}" y2="{cy}" stroke="{stroke}" stroke-width="{stroke_width}"/>
               <line x1="{cx}" y1="{cy-half}" x2="{cx}" y2="{cy+half}" stroke="{stroke}" stroke-width="{stroke_width}"/>'''


def draw_internal_x(cx: float, cy: float, size: float,
                    stroke: str = "#333", stroke_width: float = 2) -> str:
    """Draw an X pattern (diagonal cross) inside frame area."""
    half = size / 2 * 0.7
    return f'''<line x1="{cx-half}" y1="{cy-half}" x2="{cx+half}" y2="{cy+half}" stroke="{stroke}" stroke-width="{stroke_width}"/>
               <line x1="{cx+half}" y1="{cy-half}" x2="{cx-half}" y2="{cy+half}" stroke="{stroke}" stroke-width="{stroke_width}"/>'''


def draw_internal_y(cx: float, cy: float, size: float,
                    stroke: str = "#333", stroke_width: float = 2) -> str:
    """Draw a Y-shape pattern inside frame area."""
    half = size / 2 * 0.7
    # Y: two diagonal lines meeting at center, one vertical line going down
    return f'''<line x1="{cx-half}" y1="{cy-half}" x2="{cx}" y2="{cy}" stroke="{stroke}" stroke-width="{stroke_width}"/>
               <line x1="{cx+half}" y1="{cy-half}" x2="{cx}" y2="{cy}" stroke="{stroke}" stroke-width="{stroke_width}"/>
               <line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy+half}" stroke="{stroke}" stroke-width="{stroke_width}"/>'''


def draw_internal_asterisk(cx: float, cy: float, size: float,
                           stroke: str = "#333", stroke_width: float = 2) -> str:
    """Draw a 6-line asterisk (*) pattern inside frame area."""
    half = size / 2 * 0.7
    lines = []
    for i in range(6):
        angle = math.pi * i / 6
        x1 = cx - half * math.cos(angle)
        y1 = cy - half * math.sin(angle)
        x2 = cx + half * math.cos(angle)
        y2 = cy + half * math.sin(angle)
        lines.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
    return "".join(lines)


def draw_internal_t(cx: float, cy: float, size: float,
                    stroke: str = "#333", stroke_width: float = 2) -> str:
    """Draw a T-shape pattern inside frame area."""
    half = size / 2 * 0.7
    return f'''<line x1="{cx-half}" y1="{cy-half}" x2="{cx+half}" y2="{cy-half}" stroke="{stroke}" stroke-width="{stroke_width}"/>
               <line x1="{cx}" y1="{cy-half}" x2="{cx}" y2="{cy+half}" stroke="{stroke}" stroke-width="{stroke_width}"/>'''


# =============================================================================
# COMPOUND SHAPES (multiple shapes together)
# =============================================================================

def draw_overlapping_shapes(cx: float, cy: float, shape: str, count: int = 3,
                            size: float = 40, overlap: float = 0.4,
                            fill: str = "none", stroke: str = "#333") -> str:
    """Draw 2-3 overlapping shapes of the same type."""
    elements = []
    offset = size * (1 - overlap)

    if count == 2:
        positions = [
            (cx - offset/2, cy),
            (cx + offset/2, cy)
        ]
    else:  # 3 shapes
        positions = [
            (cx - offset, cy),
            (cx, cy),
            (cx + offset, cy)
        ]

    for px, py in positions:
        elements.append(draw_shape(shape, px, py, size * 0.7, fill=fill, stroke=stroke))

    return "".join(elements)


def draw_shapes_in_row(cx: float, cy: float, shapes: list, size: float = 25,
                       spacing: float = 30, fills: list = None,
                       stroke: str = "#333") -> str:
    """Draw multiple shapes arranged horizontally."""
    elements = []
    n = len(shapes)
    total_width = (n - 1) * spacing
    start_x = cx - total_width / 2

    for i, shape in enumerate(shapes):
        x = start_x + i * spacing
        fill = fills[i] if fills and i < len(fills) else "none"
        elements.append(draw_shape(shape, x, cy, size, fill=fill, stroke=stroke))

    return "".join(elements)


def draw_shapes_in_column(cx: float, cy: float, shapes: list, size: float = 25,
                          spacing: float = 30, fills: list = None,
                          stroke: str = "#333") -> str:
    """Draw multiple shapes arranged vertically."""
    elements = []
    n = len(shapes)
    total_height = (n - 1) * spacing
    start_y = cy - total_height / 2

    for i, shape in enumerate(shapes):
        y = start_y + i * spacing
        fill = fills[i] if fills and i < len(fills) else "none"
        elements.append(draw_shape(shape, cx, y, size, fill=fill, stroke=stroke))

    return "".join(elements)


def draw_parallel_lines(cx: float, cy: float, count: int = 2, length: float = 50,
                        spacing: float = 15, orientation: str = "vertical",
                        stroke: str = "#333", stroke_width: float = 2) -> str:
    """Draw parallel lines."""
    elements = []
    total_offset = (count - 1) * spacing
    start = -total_offset / 2

    for i in range(count):
        offset = start + i * spacing
        if orientation == "vertical":
            elements.append(f'<line x1="{cx + offset}" y1="{cy - length/2}" x2="{cx + offset}" y2="{cy + length/2}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
        else:
            elements.append(f'<line x1="{cx - length/2}" y1="{cy + offset}" x2="{cx + length/2}" y2="{cy + offset}" stroke="{stroke}" stroke-width="{stroke_width}"/>')

    return "".join(elements)


def draw_diagonal_arrow(cx: float, cy: float, direction: str, size: float = 30,
                        stroke: str = "#333", stroke_width: float = 2) -> str:
    """Draw arrow pointing diagonally (NE, SE, SW, NW)."""
    half = size / 2
    head_size = size / 4

    directions = {
        "ne": (1, -1),
        "se": (1, 1),
        "sw": (-1, 1),
        "nw": (-1, -1),
        "northeast": (1, -1),
        "southeast": (1, 1),
        "southwest": (-1, 1),
        "northwest": (-1, -1),
    }

    dx, dy = directions.get(direction.lower(), (1, -1))

    # Line from center-opposite to center+direction
    x1, y1 = cx - dx * half * 0.7, cy - dy * half * 0.7
    x2, y2 = cx + dx * half * 0.7, cy + dy * half * 0.7

    # Arrow head
    # Perpendicular to direction
    px, py = -dy, dx  # perpendicular unit vector

    head_pts = f"{x2},{y2} {x2 - dx*head_size + px*head_size/2},{y2 - dy*head_size + py*head_size/2} {x2 - dx*head_size - px*head_size/2},{y2 - dy*head_size - py*head_size/2}"

    return f'''<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{stroke_width}"/>
               <polygon points="{head_pts}" fill="{stroke}"/>'''


def draw_shape_with_line_through(cx: float, cy: float, shape: str, size: float,
                                 line_direction: str = "horizontal",
                                 fill: str = "none", stroke: str = "#333") -> str:
    """Draw a shape with a line passing through it."""
    elements = []
    elements.append(draw_shape(shape, cx, cy, size, fill=fill, stroke=stroke))

    margin = size * 0.6
    if line_direction == "horizontal":
        elements.append(draw_line(cx - margin, cy, cx + margin, cy, stroke=stroke))
    elif line_direction == "vertical":
        elements.append(draw_line(cx, cy - margin, cx, cy + margin, stroke=stroke))
    elif line_direction == "diagonal" or line_direction == "tlbr":
        elements.append(draw_line(cx - margin, cy - margin, cx + margin, cy + margin, stroke=stroke))
    elif line_direction == "trbl":
        elements.append(draw_line(cx + margin, cy - margin, cx - margin, cy + margin, stroke=stroke))

    return "".join(elements)


# =============================================================================
# FIGURE DESCRIPTION PARSER
# =============================================================================

def parse_figure_description(desc: str) -> dict:
    """Parse a text description of a figure into components."""
    result = {
        "outer_shape": None,
        "inner_shape": None,
        "rotation": 0,
        "size": "medium",
        "fill": "none",
        "inner_fill": "none",
        "arrow": None,
        "line": None,
        "dots": 0,
        "dots_arrangement": "line",
        "bold_sides": 0,
        "position": None,  # For small shapes at positions
        "pointing": None,  # For triangles pointing direction
        "letter": None,    # For letter-based figures
        "marker_position": None,  # For dot/circle markers
        # New fields for advanced patterns
        "divided": None,  # "quarters", "halves_vertical", "halves_horizontal", "checkerboard"
        "division_fills": None,  # list of fills for divided parts
        "pattern": None,  # "horizontal_stripes", "vertical_stripes", "diagonal_stripes", "dots", "crosshatch"
        "internal_pattern": None,  # "cross", "x", "y", "asterisk", "t"
        "overlapping": None,  # count of overlapping shapes
        "shapes_in_row": None,  # list of shapes for row layout
        "shapes_in_column": None,  # list of shapes for column layout
        "is_flag": False,  # flag/pennant shape
        "is_semicircle": False,  # half circle
        "is_half_square": False,  # half square (rectangle)
        "half_orientation": None,  # top, bottom, left, right for half shapes
        "side_by_side": False,  # two shapes side by side
        "line_through": None,  # line through shape: "horizontal", "vertical", "diagonal"
    }

    desc_lower = desc.lower()

    # Detect shapes (order matters - check more specific first)
    shapes = ["hexagon", "pentagon", "diamond", "square", "rectangle", "circle", "triangle", "star", "cross"]
    found_shapes = []
    for shape in shapes:
        if shape in desc_lower:
            found_shapes.append(shape)

    if found_shapes:
        result["outer_shape"] = found_shapes[0]
        if len(found_shapes) > 1:
            result["inner_shape"] = found_shapes[1]

    # Detect letters (R, L, T, F, etc.)
    letter_match = re.search(r"letter\s*['\"]?([A-Z])['\"]?", desc, re.IGNORECASE)
    if letter_match:
        result["letter"] = letter_match.group(1).upper()

    # Detect L-shape or T-shape explicitly
    if "l-shape" in desc_lower or "l shape" in desc_lower:
        result["outer_shape"] = "l_shape"
    if "t-shape" in desc_lower or "t shape" in desc_lower:
        result["outer_shape"] = "t_shape"

    # Detect rotation
    rotation_match = re.search(r'(\d+)\s*deg', desc_lower)
    if rotation_match:
        result["rotation"] = int(rotation_match.group(1))

    # Detect size
    if "large" in desc_lower:
        result["size"] = "large"
    elif "small" in desc_lower:
        result["size"] = "small"
    elif "medium" in desc_lower:
        result["size"] = "medium"

    # Detect fill (outer shape)
    if re.search(r'\bblack\b', desc_lower):
        result["fill"] = "#333"
    elif re.search(r'\bgrey\b|\bgray\b', desc_lower):
        result["fill"] = "#999"
    elif re.search(r'\bwhite\b', desc_lower):
        result["fill"] = "#fff"

    # Detect inner shape fill
    inner_fill_match = re.search(r'(white|black|grey|gray)\s+(circle|square|triangle|star|pentagon|hexagon)\s+inside', desc_lower)
    if inner_fill_match:
        color = inner_fill_match.group(1)
        if color == "black":
            result["inner_fill"] = "#333"
        elif color in ("grey", "gray"):
            result["inner_fill"] = "#999"
        else:
            result["inner_fill"] = "#fff"

    # Detect arrow direction
    arrow_match = re.search(r'arrow\s+(?:pointing\s+)?(up|down|left|right)', desc_lower)
    if arrow_match:
        result["arrow"] = arrow_match.group(1)

    # Detect pointing direction (for triangles)
    pointing_match = re.search(r'(?:triangle|pointing)\s+(up|down|left|right)', desc_lower)
    if pointing_match:
        result["pointing"] = pointing_match.group(1)

    # Detect line type
    if "diagonal" in desc_lower:
        if "top-left to bottom-right" in desc_lower or "tlbr" in desc_lower:
            result["line"] = "diagonal_tlbr"
        elif "top-right to bottom-left" in desc_lower or "trbl" in desc_lower:
            result["line"] = "diagonal_trbl"
        else:
            result["line"] = "diagonal_tlbr"
    elif "horizontal" in desc_lower and "line" in desc_lower:
        result["line"] = "horizontal"
    elif "vertical" in desc_lower and "line" in desc_lower:
        result["line"] = "vertical"

    # Detect dots
    dot_match = re.search(r'(\d+)\s+dots?', desc_lower)
    if dot_match:
        result["dots"] = int(dot_match.group(1))
    elif "all 4 corners" in desc_lower or "dots in all" in desc_lower:
        result["dots"] = 4

    # Detect dot arrangement
    if "triangle" in desc_lower and "arranged" in desc_lower:
        result["dots_arrangement"] = "triangle"
    elif "square" in desc_lower and "arranged" in desc_lower:
        result["dots_arrangement"] = "square"
    elif "diamond" in desc_lower and "arranged" in desc_lower:
        result["dots_arrangement"] = "diamond"
    elif "line" in desc_lower and ("arranged" in desc_lower or "in" in desc_lower):
        result["dots_arrangement"] = "line"

    # Detect bold sides
    bold_match = re.search(r'(\d+)\s+(?:adjacent\s+)?sides?\s+bold', desc_lower)
    if bold_match:
        result["bold_sides"] = int(bold_match.group(1))
    elif "all" in desc_lower and ("bold" in desc_lower or "5 sides bold" in desc_lower):
        result["bold_sides"] = 5

    # Detect position for compound figures
    if "top-right" in desc_lower or "top right" in desc_lower:
        result["position"] = "top-right"
    elif "top-left" in desc_lower or "top left" in desc_lower:
        result["position"] = "top-left"
    elif "bottom-right" in desc_lower or "bottom right" in desc_lower:
        result["position"] = "bottom-right"
    elif "bottom-left" in desc_lower or "bottom left" in desc_lower:
        result["position"] = "bottom-left"
    elif "on left" in desc_lower:
        result["position"] = "left"
    elif "on right" in desc_lower:
        result["position"] = "right"

    # Detect marker position (for rotation questions)
    marker_match = re.search(r'(?:circle|dot|marker)\s+(?:at\s+|in\s+)?(top-right|top-left|bottom-right|bottom-left|top|bottom|left|right)', desc_lower)
    if marker_match:
        result["marker_position"] = marker_match.group(1)

    # ==========================================================================
    # NEW PATTERN DETECTION
    # ==========================================================================

    # Detect flag/pennant shape
    if "flag" in desc_lower or "pennant" in desc_lower:
        result["is_flag"] = True
        result["outer_shape"] = "flag"
        # Detect flag direction
        if "pointing up" in desc_lower or "flag up" in desc_lower:
            result["pointing"] = "up"
        elif "pointing down" in desc_lower or "flag down" in desc_lower:
            result["pointing"] = "down"
        elif "pointing left" in desc_lower or "flag left" in desc_lower:
            result["pointing"] = "left"
        else:
            result["pointing"] = "right"  # default

    # Detect semicircle / half circle
    if "semicircle" in desc_lower or "half circle" in desc_lower:
        result["is_semicircle"] = True
        result["outer_shape"] = "semicircle"
        # Detect orientation
        if "top" in desc_lower:
            result["half_orientation"] = "top"
        elif "bottom" in desc_lower:
            result["half_orientation"] = "bottom"
        elif "left" in desc_lower:
            result["half_orientation"] = "left"
        elif "right" in desc_lower:
            result["half_orientation"] = "right"
        else:
            result["half_orientation"] = "top"

    # Detect half square
    if "half square" in desc_lower:
        result["is_half_square"] = True
        result["outer_shape"] = "half_square"
        if "half the width" in desc_lower:
            result["half_orientation"] = "left"
        elif "half the height" in desc_lower:
            result["half_orientation"] = "top"

    # Detect divided shapes
    divided_match = re.search(r'divided\s+(?:into\s+)?(\d+)\s*(?:equal\s+)?(?:parts?|quarters?|halves?)', desc_lower)
    if divided_match:
        num_parts = int(divided_match.group(1))
        if num_parts == 4:
            result["divided"] = "quarters"
        elif num_parts == 2:
            if "vertical" in desc_lower or "left" in desc_lower or "right" in desc_lower:
                result["divided"] = "halves_vertical"
            else:
                result["divided"] = "halves_horizontal"

    # Also detect "divided vertically/horizontally"
    if "divided vertically" in desc_lower:
        result["divided"] = "halves_vertical"
    elif "divided horizontally" in desc_lower:
        result["divided"] = "halves_horizontal"

    # Detect checkerboard pattern
    if "checkerboard" in desc_lower or "alternating black-white" in desc_lower:
        result["divided"] = "checkerboard"

    # Parse division fills from description
    if result["divided"]:
        fills = []
        # Look for color specifications per part
        if result["divided"] == "quarters":
            # Parse quarter fills: "top-left black, rest white"
            quarter_pattern = r'(top-left|top-right|bottom-left|bottom-right)\s+(black|white|grey|gray)'
            quarter_matches = re.findall(quarter_pattern, desc_lower)

            # Default all to white
            quarter_fills = {"top-left": "#fff", "top-right": "#fff", "bottom-right": "#fff", "bottom-left": "#fff"}

            for pos, color in quarter_matches:
                color_val = "#333" if color == "black" else "#999" if color in ("grey", "gray") else "#fff"
                quarter_fills[pos] = color_val

            # Check for "rest white/black"
            if "rest white" in desc_lower:
                for k in quarter_fills:
                    if quarter_fills[k] == "#fff":
                        pass  # already white
            elif "rest black" in desc_lower:
                for k in quarter_fills:
                    if quarter_fills[k] != "#333":
                        quarter_fills[k] = "#333"

            fills = [quarter_fills["top-left"], quarter_fills["top-right"],
                    quarter_fills["bottom-right"], quarter_fills["bottom-left"]]

        elif result["divided"] in ("halves_vertical", "halves_horizontal"):
            # Parse half fills: "left half black, right half white"
            left_fill = "#fff"
            right_fill = "#fff"
            top_fill = "#fff"
            bottom_fill = "#fff"

            if "left" in desc_lower and "black" in desc_lower:
                if re.search(r'left\s+(?:half\s+)?(?:is\s+)?(?:has\s+)?black', desc_lower):
                    left_fill = "#333"
            if "right" in desc_lower and "black" in desc_lower:
                if re.search(r'right\s+(?:half\s+)?(?:is\s+)?(?:has\s+)?black', desc_lower):
                    right_fill = "#333"
            if "top" in desc_lower and "black" in desc_lower:
                if re.search(r'top\s+(?:half\s+)?(?:is\s+)?(?:has\s+)?black', desc_lower):
                    top_fill = "#333"
            if "bottom" in desc_lower and "black" in desc_lower:
                if re.search(r'bottom\s+(?:half\s+)?(?:is\s+)?(?:has\s+)?black', desc_lower):
                    bottom_fill = "#333"

            if result["divided"] == "halves_vertical":
                fills = [left_fill, right_fill]
            else:
                fills = [top_fill, bottom_fill]

        elif result["divided"] == "checkerboard":
            fills = ["#333", "#fff"]

        result["division_fills"] = fills if fills else None

    # Detect pattern fills (stripes, dots, crosshatch)
    if "horizontal stripes" in desc_lower or "horizontal stripe" in desc_lower:
        result["pattern"] = "horizontal_stripes"
    elif "vertical stripes" in desc_lower or "vertical stripe" in desc_lower:
        result["pattern"] = "vertical_stripes"
    elif "diagonal stripes" in desc_lower or "diagonal stripe" in desc_lower:
        result["pattern"] = "diagonal_stripes"
    elif "crosshatch" in desc_lower or "cross-hatch" in desc_lower:
        result["pattern"] = "crosshatch"
    elif re.search(r'(?:has\s+)?dots\s+(?:pattern|inside)', desc_lower):
        result["pattern"] = "dots"
    elif "striped" in desc_lower:
        result["pattern"] = "diagonal_stripes"  # default stripe direction

    # Detect internal patterns (inside shape frames)
    if "plus sign inside" in desc_lower or "plus inside" in desc_lower or "+ inside" in desc_lower:
        result["internal_pattern"] = "cross"
    elif "diagonal cross inside" in desc_lower or "x-shape inside" in desc_lower or "x inside" in desc_lower:
        result["internal_pattern"] = "x"
    elif "y-shape inside" in desc_lower or "y inside" in desc_lower:
        result["internal_pattern"] = "y"
    elif "asterisk inside" in desc_lower or "* inside" in desc_lower:
        result["internal_pattern"] = "asterisk"
    elif "t-shape inside" in desc_lower or "t inside" in desc_lower:
        result["internal_pattern"] = "t"

    # Detect overlapping shapes
    overlap_match = re.search(r'(\d+|two|three)\s+overlapping\s+(\w+)', desc_lower)
    if overlap_match:
        count_str = overlap_match.group(1)
        if count_str == "two":
            result["overlapping"] = 2
        elif count_str == "three":
            result["overlapping"] = 3
        else:
            result["overlapping"] = int(count_str)

    # Detect multi-shape layouts
    row_match = re.search(r'(\d+)\s+shapes?\s+in\s+(?:a\s+)?row', desc_lower)
    if row_match:
        # Try to extract shape names
        shapes_match = re.search(r':\s*([^-]+?)(?:\s*-|$)', desc_lower)
        if shapes_match:
            shape_list = shapes_match.group(1).strip().split(',')
            shape_list = [s.strip() for s in shape_list]
            result["shapes_in_row"] = shape_list

    column_match = re.search(r'(\d+)\s+shapes?\s+in\s+(?:a\s+)?column', desc_lower)
    if column_match:
        shapes_match = re.search(r':\s*([^-]+?)(?:\s*-|$)', desc_lower)
        if shapes_match:
            shape_list = shapes_match.group(1).strip().split(',')
            shape_list = [s.strip() for s in shape_list]
            result["shapes_in_column"] = shape_list

    # Detect "side by side"
    if "side by side" in desc_lower:
        result["side_by_side"] = True

    # Detect line through shape
    if "line through" in desc_lower:
        if "horizontal" in desc_lower:
            result["line_through"] = "horizontal"
        elif "vertical" in desc_lower:
            result["line_through"] = "vertical"
        elif "diagonal" in desc_lower:
            result["line_through"] = "diagonal"
        else:
            result["line_through"] = "horizontal"  # default

    return result


def get_size_value(size_name: str) -> int:
    """Convert size name to pixel value."""
    sizes = {"large": 70, "medium": 50, "small": 35}
    return sizes.get(size_name, 50)


def get_fill_color(fill_name: str) -> str:
    """Convert fill name to color value."""
    if fill_name in ("#333", "#999", "#fff", "none"):
        return fill_name
    fills = {"black": "#333", "grey": "#999", "gray": "#999", "white": "#fff"}
    return fills.get(fill_name, "none")


# =============================================================================
# FIGURE RENDERING
# =============================================================================

def render_figure(parsed: dict, width: int = OPTION_SIZE, height: int = OPTION_SIZE) -> str:
    """Render a parsed figure description to SVG elements."""
    cx, cy = width / 2, height / 2
    elements = []

    outer_size = get_size_value(parsed["size"])
    inner_size = outer_size * 0.4

    fill = parsed["fill"]
    stroke = "#fff" if fill == "#333" else "#333"

    # ==========================================================================
    # HANDLE NEW SPECIAL SHAPES FIRST (flag, semicircle, half_square)
    # ==========================================================================

    # Handle flag/pennant shape
    if parsed.get("is_flag") or parsed.get("outer_shape") == "flag":
        direction = parsed.get("pointing", "right")
        elements.append(draw_flag(cx, cy, outer_size, direction, fill=fill, stroke=stroke))
        # Skip normal shape rendering
        return "".join(elements)

    # Handle semicircle
    if parsed.get("is_semicircle") or parsed.get("outer_shape") == "semicircle":
        orientation = parsed.get("half_orientation", "top")
        elements.append(draw_semicircle(cx, cy, outer_size/2, orientation, fill=fill, stroke=stroke))
        return "".join(elements)

    # Handle half square
    if parsed.get("is_half_square") or parsed.get("outer_shape") == "half_square":
        orientation = parsed.get("half_orientation", "left")
        elements.append(draw_half_square(cx, cy, outer_size, orientation, fill=fill, stroke=stroke))
        return "".join(elements)

    # ==========================================================================
    # HANDLE OVERLAPPING SHAPES
    # ==========================================================================

    if parsed.get("overlapping"):
        shape = parsed.get("outer_shape", "circle")
        count = parsed["overlapping"]
        elements.append(draw_overlapping_shapes(cx, cy, shape, count, outer_size, fill=fill, stroke=stroke))
        return "".join(elements)

    # ==========================================================================
    # HANDLE SHAPES IN ROW/COLUMN
    # ==========================================================================

    if parsed.get("shapes_in_row"):
        shapes = parsed["shapes_in_row"]
        elements.append(draw_shapes_in_row(cx, cy, shapes, size=outer_size*0.5, spacing=outer_size*0.7, stroke=stroke))
        return "".join(elements)

    if parsed.get("shapes_in_column"):
        shapes = parsed["shapes_in_column"]
        elements.append(draw_shapes_in_column(cx, cy, shapes, size=outer_size*0.5, spacing=outer_size*0.7, stroke=stroke))
        return "".join(elements)

    # ==========================================================================
    # HANDLE SIDE BY SIDE (two triangles, etc.)
    # ==========================================================================

    if parsed.get("side_by_side") and parsed.get("outer_shape"):
        shape = parsed["outer_shape"]
        elements.append(draw_shapes_in_row(cx, cy, [shape, shape], size=outer_size*0.5, spacing=outer_size*0.6, stroke=stroke))
        return "".join(elements)

    # ==========================================================================
    # HANDLE DIVIDED SHAPES
    # ==========================================================================

    if parsed.get("divided") and parsed.get("outer_shape"):
        shape = parsed["outer_shape"]
        fills = parsed.get("division_fills", ["#fff", "#333"])
        division = parsed["divided"]

        if division == "quarters":
            if shape == "circle":
                elements.append(draw_divided_circle(cx, cy, outer_size/2, fills, stroke=stroke))
            elif shape in ("square", "rectangle"):
                elements.append(draw_divided_square(cx, cy, outer_size, fills, division="quarters", stroke=stroke))
            else:
                elements.append(draw_divided_shape(cx, cy, outer_size, shape, fills, division="quarters", stroke=stroke))

        elif division == "halves_vertical":
            if shape == "circle":
                elements.append(draw_divided_circle(cx, cy, outer_size/2, fills[:2], stroke=stroke))
            elif shape in ("square", "rectangle"):
                elements.append(draw_divided_square(cx, cy, outer_size, fills[:2], division="vertical", stroke=stroke))
            else:
                elements.append(draw_divided_shape(cx, cy, outer_size, shape, fills[:2], division="vertical", stroke=stroke))

        elif division == "halves_horizontal":
            if shape in ("square", "rectangle"):
                elements.append(draw_divided_square(cx, cy, outer_size, fills[:2], division="horizontal", stroke=stroke))
            else:
                elements.append(draw_divided_shape(cx, cy, outer_size, shape, fills[:2], division="horizontal", stroke=stroke))

        elif division == "checkerboard":
            if shape in ("square", "rectangle"):
                elements.append(draw_divided_square(cx, cy, outer_size, fills, division="checkerboard", stroke=stroke))

        # After drawing divided shape, we can add internal patterns if present
        if parsed.get("internal_pattern"):
            pattern = parsed["internal_pattern"]
            pattern_funcs = {
                "cross": draw_internal_cross,
                "x": draw_internal_x,
                "y": draw_internal_y,
                "asterisk": draw_internal_asterisk,
                "t": draw_internal_t,
            }
            if pattern in pattern_funcs:
                elements.append(pattern_funcs[pattern](cx, cy, outer_size * 0.8, stroke=stroke))

        return "".join(elements)

    # ==========================================================================
    # HANDLE SHAPE WITH LINE THROUGH
    # ==========================================================================

    if parsed.get("line_through") and parsed.get("outer_shape"):
        shape = parsed["outer_shape"]
        direction = parsed["line_through"]
        elements.append(draw_shape_with_line_through(cx, cy, shape, outer_size, direction, fill=fill, stroke=stroke))
        return "".join(elements)

    # ==========================================================================
    # STANDARD SHAPE RENDERING
    # ==========================================================================

    # Draw outer shape
    if parsed["outer_shape"]:
        rotation = parsed["rotation"]
        pointing = parsed.get("pointing")

        # Adjust rotation for pointing direction
        if parsed["outer_shape"] == "triangle" and pointing:
            directions = {"up": 0, "right": 90, "down": 180, "left": 270}
            rotation = directions.get(pointing, 0)

        if parsed["outer_shape"] == "l_shape":
            elements.append(draw_l_shape(cx, cy, outer_size, rotation, fill, stroke))
        elif parsed["outer_shape"] == "t_shape":
            elements.append(draw_t_shape(cx, cy, outer_size, rotation, fill, stroke))
        else:
            elements.append(draw_shape(
                parsed["outer_shape"], cx, cy, outer_size,
                fill=fill, stroke=stroke, rotation=rotation
            ))

    # Draw inner shape
    if parsed["inner_shape"]:
        inner_fill = parsed.get("inner_fill", "none")
        inner_stroke = "#fff" if inner_fill == "#333" else "#333"
        elements.append(draw_shape(
            parsed["inner_shape"], cx, cy, inner_size,
            fill=inner_fill, stroke=inner_stroke
        ))

    # Draw internal pattern (for frame + pattern combinations)
    if parsed.get("internal_pattern"):
        pattern = parsed["internal_pattern"]
        pattern_funcs = {
            "cross": draw_internal_cross,
            "x": draw_internal_x,
            "y": draw_internal_y,
            "asterisk": draw_internal_asterisk,
            "t": draw_internal_t,
        }
        if pattern in pattern_funcs:
            elements.append(pattern_funcs[pattern](cx, cy, outer_size * 0.7, stroke=stroke))

    # Draw letter
    if parsed["letter"]:
        rotation = parsed["rotation"]
        elements.append(draw_letter(parsed["letter"], cx, cy, outer_size * 0.6, rotation))

    # Draw arrow
    if parsed["arrow"]:
        elements.append(draw_arrow(cx, cy, parsed["arrow"], size=30))

    # Draw internal line
    if parsed["line"]:
        margin = 15
        if parsed["line"] == "diagonal_tlbr":
            elements.append(draw_line(margin, margin, width-margin, height-margin))
        elif parsed["line"] == "diagonal_trbl":
            elements.append(draw_line(width-margin, margin, margin, height-margin))
        elif parsed["line"] == "horizontal":
            elements.append(draw_line(margin, cy, width-margin, cy))
        elif parsed["line"] == "vertical":
            elements.append(draw_line(cx, margin, cx, height-margin))

    # Draw dots
    if parsed["dots"] > 0:
        if "below" in str(parsed.get("dots_arrangement", "")):
            elements.append(draw_dots_below(parsed["dots"], cx, height - 15))
        elif parsed.get("dots_arrangement") in ("triangle", "square", "diamond"):
            elements.append(draw_dots_inside(parsed["dots"], cx, cy, parsed["dots_arrangement"]))
        else:
            elements.append(draw_dots_below(parsed["dots"], cx, height - 15))

    # Draw bold sides (for pentagon)
    if parsed["bold_sides"] > 0 and parsed["outer_shape"] == "pentagon":
        # Overlay bold lines for specified sides
        r = outer_size / 2
        for i in range(parsed["bold_sides"]):
            angle1 = (2 * math.pi * i / 5) - math.pi/2 - math.pi/2
            angle2 = (2 * math.pi * (i + 1) / 5) - math.pi/2 - math.pi/2
            x1 = cx + r * math.cos(angle1)
            y1 = cy + r * math.sin(angle1)
            x2 = cx + r * math.cos(angle2)
            y2 = cy + r * math.sin(angle2)
            elements.append(draw_line(x1, y1, x2, y2, bold=True))

    # Draw marker at position
    if parsed.get("marker_position"):
        pos = parsed["marker_position"]
        margin = 15
        marker_positions = {
            "top-left": (margin, margin),
            "top-right": (width - margin, margin),
            "bottom-left": (margin, height - margin),
            "bottom-right": (width - margin, height - margin),
            "top": (cx, margin),
            "bottom": (cx, height - margin),
            "left": (margin, cy),
            "right": (width - margin, cy),
        }
        if pos in marker_positions:
            mx, my = marker_positions[pos]
            elements.append(draw_dot(mx, my, 5))

    return "".join(elements)


def render_compound_figure(desc: str, width: int = OPTION_SIZE, height: int = OPTION_SIZE) -> str:
    """Render more complex compound figures with multiple elements."""
    elements = []
    cx, cy = width / 2, height / 2
    desc_lower = desc.lower()

    # Handle "shape on left, shape on right" patterns
    if "on left" in desc_lower and "on right" in desc_lower:
        left_part = re.search(r'(.+?)\s+on\s+left', desc_lower)
        right_part = re.search(r'(.+?)\s+on\s+right', desc_lower)

        if left_part:
            left_parsed = parse_figure_description(left_part.group(1))
            left_size = get_size_value(left_parsed.get("size", "medium"))
            left_fill = left_parsed.get("fill", "none")
            if left_parsed["outer_shape"]:
                elements.append(draw_shape(
                    left_parsed["outer_shape"], cx - 25, cy, left_size * 0.7,
                    fill=left_fill, stroke="#333"
                ))

        if right_part:
            right_parsed = parse_figure_description(right_part.group(1))
            right_size = get_size_value(right_parsed.get("size", "medium"))
            right_fill = right_parsed.get("fill", "none")
            if right_parsed["outer_shape"]:
                elements.append(draw_shape(
                    right_parsed["outer_shape"], cx + 25, cy, right_size * 0.7,
                    fill=right_fill, stroke="#333"
                ))

        # Check for line above/below
        if "line above" in desc_lower:
            elements.append(draw_line(15, 15, width - 15, 15))
        if "line below" in desc_lower:
            elements.append(draw_line(15, height - 15, width - 15, height - 15))

        return "".join(elements)

    # Handle small shape at position (e.g., "Large black circle, small white square at top-right")
    parsed = parse_figure_description(desc)

    if parsed["outer_shape"] and parsed["position"]:
        # Main shape in center
        main_size = get_size_value(parsed["size"])
        elements.append(draw_shape(
            parsed["outer_shape"], cx, cy, main_size,
            fill=parsed["fill"], stroke="#333"
        ))

        # Small shape at position
        if parsed["inner_shape"]:
            pos_offsets = {
                "top-right": (width - 20, 20),
                "top-left": (20, 20),
                "bottom-right": (width - 20, height - 20),
                "bottom-left": (20, height - 20),
            }
            if parsed["position"] in pos_offsets:
                px, py = pos_offsets[parsed["position"]]
                inner_fill = parsed.get("inner_fill", "none")
                elements.append(draw_shape(
                    parsed["inner_shape"], px, py, 20,
                    fill=inner_fill, stroke="#333"
                ))

        return "".join(elements)

    # Fall back to standard rendering
    return render_figure(parsed, width, height)


# =============================================================================
# TYPE-SPECIFIC SVG GENERATORS
# =============================================================================

def generate_sequences_svgs(question: dict) -> dict:
    """Generate SVGs for nvr_sequences questions."""
    q_id = question.get("id", "seq")
    text = question["content"]["text"]
    options = question["content"].get("options", [])

    updates = {}

    # Generate main sequence image
    fig_pattern = r'Fig\s*\d+:\s*([^\n]+)'
    figures = re.findall(fig_pattern, text)

    if figures:
        num_figs = len(figures)
        fig_width = 100
        total_width = num_figs * fig_width + 20
        height = 120

        svg_parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_width} {height}" width="{total_width}" height="{height}">']
        svg_parts.append('<rect width="100%" height="100%" fill="#f8f9fa"/>')

        for i, fig_desc in enumerate(figures):
            x_offset = i * fig_width + 10

            svg_parts.append(f'<g transform="translate({x_offset}, 0)">')
            svg_parts.append(f'<text x="50" y="15" text-anchor="middle" font-size="12" fill="#666">{i+1}</text>')
            svg_parts.append('<rect x="5" y="20" width="90" height="90" fill="white" stroke="#ddd" rx="4"/>')

            # Check if this is the last figure with "?"
            if "?" in fig_desc:
                svg_parts.append('<text x="50" y="75" text-anchor="middle" font-size="36" fill="#999">?</text>')
            else:
                parsed = parse_figure_description(fig_desc)
                fig_elements = render_figure(parsed, 90, 90)
                svg_parts.append(f'<g transform="translate(5, 20)">{fig_elements}</g>')

            svg_parts.append('</g>')

        svg_parts.append('</svg>')
        main_svg = "".join(svg_parts)
        filename = f"{q_id}_main.svg"
        updates["image_url"] = save_svg(main_svg, filename)

    # Generate option SVGs
    option_paths = []
    for i, opt in enumerate(options):
        desc = re.sub(r'^[A-E]:\s*', '', opt)
        parsed = parse_figure_description(desc)

        svg_parts = [create_svg_header(OPTION_SIZE, OPTION_SIZE)]
        svg_parts.append('<rect width="100%" height="100%" fill="white" stroke="#ddd" rx="4"/>')
        svg_parts.append(render_figure(parsed, OPTION_SIZE, OPTION_SIZE))
        svg_parts.append(create_svg_footer())

        filename = f"{q_id}_opt_{chr(65+i)}.svg"
        path = save_svg("".join(svg_parts), filename)
        option_paths.append(path)

    if option_paths:
        updates["images"] = option_paths

    return updates


def generate_odd_one_out_svgs(question: dict) -> dict:
    """Generate SVGs for nvr_odd_one_out questions.

    These questions have options as just letters (A, B, C, D, E) but the
    figure descriptions are in the question text.
    """
    q_id = question.get("id", "odd")
    text = question["content"]["text"]

    updates = {}

    # Parse figure descriptions from question text
    # Format: "A: description\nB: description\n..."
    option_pattern = r'([A-E]):\s*([^\n]+)'
    option_descs = re.findall(option_pattern, text)

    if not option_descs:
        return updates

    # =========================================================================
    # Generate main figure showing all 5 options in a row labeled A-E
    # =========================================================================
    num_options = len(option_descs)
    fig_width = 100
    total_width = num_options * fig_width + 20
    height = 130

    main_svg_parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_width} {height}" width="{total_width}" height="{height}">']
    main_svg_parts.append('<rect width="100%" height="100%" fill="#f8f9fa"/>')

    main_pattern_counter = 0
    for i, (letter, desc) in enumerate(option_descs):
        x_offset = i * fig_width + 10
        desc_lower = desc.lower()

        main_svg_parts.append(f'<g transform="translate({x_offset}, 0)">')
        # Label above the figure
        main_svg_parts.append(f'<text x="50" y="15" text-anchor="middle" font-size="14" font-weight="bold" fill="#333">{letter}</text>')
        main_svg_parts.append('<rect x="5" y="22" width="90" height="90" fill="white" stroke="#ddd" rx="4"/>')

        # Render the figure using same logic as option rendering
        fig_elements = ""
        if "divided" in desc_lower and ("stripes" in desc_lower or "dots" in desc_lower or "crosshatch" in desc_lower):
            svg_content = render_divided_shape_with_pattern(desc, 90, 90, main_pattern_counter)
            main_pattern_counter += 1
            # Insert pattern defs
            main_svg_parts.insert(1, svg_content[0])
            fig_elements = svg_content[1]
        elif " on left" in desc_lower or " on right" in desc_lower or " at " in desc_lower:
            fig_elements = render_compound_figure(desc, 90, 90)
        else:
            parsed = parse_figure_description(desc)
            fig_elements = render_figure(parsed, 90, 90)

        main_svg_parts.append(f'<g transform="translate(5, 22)">{fig_elements}</g>')
        main_svg_parts.append('</g>')

    main_svg_parts.append('</svg>')
    main_svg = "".join(main_svg_parts)
    main_filename = f"{q_id}_main.svg"
    updates["image_url"] = save_svg(main_svg, main_filename)

    # =========================================================================
    # Generate individual option SVGs
    # =========================================================================
    option_paths = []
    pattern_counter = 0  # For unique pattern IDs

    for letter, desc in option_descs:
        desc_lower = desc.lower()
        svg_parts = [create_svg_header(OPTION_SIZE, OPTION_SIZE)]
        svg_parts.append('<rect width="100%" height="100%" fill="white" stroke="#ddd" rx="4"/>')

        cx, cy = OPTION_SIZE / 2, OPTION_SIZE / 2

        # Special handling for divided shapes with pattern fills (odd-005 style)
        if "divided" in desc_lower and ("stripes" in desc_lower or "dots" in desc_lower or "crosshatch" in desc_lower):
            svg_content = render_divided_shape_with_pattern(desc, OPTION_SIZE, OPTION_SIZE, pattern_counter)
            pattern_counter += 1
            svg_parts.insert(1, svg_content[0])  # Insert pattern defs after header
            svg_parts.append(svg_content[1])  # Add shape

        # Use compound figure renderer for complex descriptions
        elif " on left" in desc_lower or " on right" in desc_lower or " at " in desc_lower:
            svg_parts.append(render_compound_figure(desc, OPTION_SIZE, OPTION_SIZE))

        else:
            parsed = parse_figure_description(desc)
            svg_parts.append(render_figure(parsed, OPTION_SIZE, OPTION_SIZE))

        svg_parts.append(create_svg_footer())

        filename = f"{q_id}_opt_{letter}.svg"
        path = save_svg("".join(svg_parts), filename)
        option_paths.append(path)

    if option_paths:
        updates["images"] = option_paths

    return updates


def render_divided_shape_with_pattern(desc: str, width: int, height: int, pattern_id_base: int) -> tuple:
    """Render a shape divided with pattern fills.

    Returns tuple of (defs_string, shape_string).
    """
    desc_lower = desc.lower()
    cx, cy = width / 2, height / 2
    size = 60

    # Detect shape
    shape = "circle"
    for s in ["hexagon", "pentagon", "rectangle", "square", "circle", "triangle"]:
        if s in desc_lower:
            shape = s
            break

    # Detect pattern type for left half
    pattern_type = "horizontal_stripes"
    if "horizontal stripes" in desc_lower:
        pattern_type = "horizontal_stripes"
    elif "vertical stripes" in desc_lower:
        pattern_type = "vertical_stripes"
    elif "diagonal stripes" in desc_lower:
        pattern_type = "diagonal_stripes"
    elif "crosshatch" in desc_lower:
        pattern_type = "crosshatch"
    elif "dots" in desc_lower:
        pattern_type = "dots"

    # Detect right half fill
    right_fill = "#fff"
    if "right half is black" in desc_lower or "right half black" in desc_lower or "right is black" in desc_lower:
        right_fill = "#333"
    elif "right half is white" in desc_lower or "right half white" in desc_lower or "right is white" in desc_lower:
        right_fill = "#fff"
    elif "right half is grey" in desc_lower or "right half grey" in desc_lower or "right is grey" in desc_lower:
        right_fill = "#999"
    # Also check simpler patterns
    if re.search(r'right\s+(?:half\s+)?(?:is\s+)?black', desc_lower):
        right_fill = "#333"
    elif re.search(r'right\s+(?:half\s+)?(?:is\s+)?white', desc_lower):
        right_fill = "#fff"
    elif re.search(r'right\s+(?:half\s+)?(?:is\s+)?grey', desc_lower):
        right_fill = "#999"

    # Create pattern definition
    pattern_id = f"pattern_{pattern_id_base}"
    if pattern_type == "horizontal_stripes":
        defs = create_stripe_pattern(pattern_id, "horizontal")
    elif pattern_type == "vertical_stripes":
        defs = create_stripe_pattern(pattern_id, "vertical")
    elif pattern_type == "diagonal_stripes":
        defs = create_stripe_pattern(pattern_id, "diagonal")
    elif pattern_type == "crosshatch":
        defs = create_crosshatch_pattern(pattern_id)
    elif pattern_type == "dots":
        defs = create_dots_pattern(pattern_id)
    else:
        defs = create_stripe_pattern(pattern_id, "horizontal")

    left_fill = f"url(#{pattern_id})"

    # Draw the divided shape
    elements = []
    half = size / 2

    if shape == "circle":
        r = size / 2
        # Left half with pattern
        elements.append(f'<path d="M {cx},{cy-r} A {r},{r} 0 0 0 {cx},{cy+r} Z" fill="{left_fill}" stroke="#333" stroke-width="2"/>')
        # Right half
        elements.append(f'<path d="M {cx},{cy-r} A {r},{r} 0 0 1 {cx},{cy+r} Z" fill="{right_fill}" stroke="#333" stroke-width="2"/>')
        # Outline
        elements.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#333" stroke-width="2"/>')

    elif shape in ("square", "rectangle"):
        # Left half with pattern
        elements.append(f'<rect x="{cx-half}" y="{cy-half}" width="{half}" height="{size}" fill="{left_fill}" stroke="#333" stroke-width="2"/>')
        # Right half
        elements.append(f'<rect x="{cx}" y="{cy-half}" width="{half}" height="{size}" fill="{right_fill}" stroke="#333" stroke-width="2"/>')
        # Outline
        elements.append(f'<rect x="{cx-half}" y="{cy-half}" width="{size}" height="{size}" fill="none" stroke="#333" stroke-width="2"/>')

    elif shape == "triangle":
        h = size * 0.866
        top = (cx, cy - h/2)
        bl = (cx - size/2, cy + h/2)
        br = (cx + size/2, cy + h/2)
        mid_bottom = (cx, cy + h/2)
        # Left half
        elements.append(f'<polygon points="{top[0]},{top[1]} {bl[0]},{bl[1]} {mid_bottom[0]},{mid_bottom[1]}" fill="{left_fill}" stroke="#333" stroke-width="2"/>')
        # Right half
        elements.append(f'<polygon points="{top[0]},{top[1]} {mid_bottom[0]},{mid_bottom[1]} {br[0]},{br[1]}" fill="{right_fill}" stroke="#333" stroke-width="2"/>')
        # Outline
        elements.append(f'<polygon points="{top[0]},{top[1]} {bl[0]},{bl[1]} {br[0]},{br[1]}" fill="none" stroke="#333" stroke-width="2"/>')

    elif shape == "hexagon":
        r = size / 2
        points = []
        for i in range(6):
            angle = (2 * math.pi * i / 6)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            points.append((x, y))

        # Left half (points 2, 3, 4 and center)
        left_pts = f"{cx},{cy} {points[2][0]:.1f},{points[2][1]:.1f} {points[3][0]:.1f},{points[3][1]:.1f} {points[4][0]:.1f},{points[4][1]:.1f}"
        elements.append(f'<polygon points="{left_pts}" fill="{left_fill}" stroke="#333" stroke-width="2"/>')
        # Right half (points 5, 0, 1 and center)
        right_pts = f"{cx},{cy} {points[5][0]:.1f},{points[5][1]:.1f} {points[0][0]:.1f},{points[0][1]:.1f} {points[1][0]:.1f},{points[1][1]:.1f}"
        elements.append(f'<polygon points="{right_pts}" fill="{right_fill}" stroke="#333" stroke-width="2"/>')
        # Outline
        pts_str = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in points)
        elements.append(f'<polygon points="{pts_str}" fill="none" stroke="#333" stroke-width="2"/>')

    elif shape == "pentagon":
        r = size / 2
        points = []
        for i in range(5):
            angle = (2 * math.pi * i / 5) - math.pi/2
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            points.append((x, y))

        # Simplified vertical split
        left_pts = f"{cx},{cy} {points[0][0]:.1f},{points[0][1]:.1f} {points[3][0]:.1f},{points[3][1]:.1f} {points[4][0]:.1f},{points[4][1]:.1f}"
        elements.append(f'<polygon points="{left_pts}" fill="{left_fill}" stroke="#333" stroke-width="2"/>')
        right_pts = f"{cx},{cy} {points[0][0]:.1f},{points[0][1]:.1f} {points[1][0]:.1f},{points[1][1]:.1f} {points[2][0]:.1f},{points[2][1]:.1f} {points[3][0]:.1f},{points[3][1]:.1f}"
        elements.append(f'<polygon points="{right_pts}" fill="{right_fill}" stroke="#333" stroke-width="2"/>')
        # Outline
        pts_str = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in points)
        elements.append(f'<polygon points="{pts_str}" fill="none" stroke="#333" stroke-width="2"/>')

    return (defs, "".join(elements))


def generate_analogies_svgs(question: dict) -> dict:
    """Generate SVGs for nvr_analogies questions."""
    q_id = question.get("id", "ana")
    text = question["content"].get("text", "")
    options = question["content"].get("options", [])

    updates = {}

    # =========================================================================
    # Generate main figure showing the analogy: A is to B as C is to ?
    # =========================================================================
    # Parse bracketed descriptions from question text
    # Format: "[desc1] is to [desc2] as [desc3] is to [?]"
    bracket_pattern = r'\[([^\]]+)\]'
    bracketed_descs = re.findall(bracket_pattern, text)

    # We expect 3-4 bracketed descriptions (last may be "?")
    if len(bracketed_descs) >= 3:
        # Filter out "?" entries
        fig_descs = [d for d in bracketed_descs if d.strip() != "?"]

        # Layout: 4 boxes with labels between them
        # [Fig1] "is to" [Fig2] "as" [Fig3] "is to" [?]
        box_width = 90
        label_width = 50
        total_width = 4 * box_width + 3 * label_width + 40
        height = 130

        main_svg_parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_width} {height}" width="{total_width}" height="{height}">']
        main_svg_parts.append('<rect width="100%" height="100%" fill="#f8f9fa"/>')

        positions = []  # Store x positions for boxes
        x = 20

        for i in range(4):  # 4 boxes total
            positions.append(x)

            # Draw the box
            main_svg_parts.append(f'<rect x="{x}" y="25" width="{box_width}" height="{box_width}" fill="white" stroke="#ddd" rx="4"/>')

            # Render figure or question mark
            if i < len(fig_descs):
                desc = fig_descs[i]
                parsed = parse_figure_description(desc)
                fig_elements = render_figure(parsed, box_width, box_width)
                main_svg_parts.append(f'<g transform="translate({x}, 25)">{fig_elements}</g>')
            else:
                # Question mark for the answer slot
                main_svg_parts.append(f'<text x="{x + box_width/2}" y="{25 + box_width/2 + 12}" text-anchor="middle" font-size="40" fill="#999">?</text>')

            x += box_width

            # Add label between boxes
            if i == 0:
                # "is to"
                main_svg_parts.append(f'<text x="{x + label_width/2}" y="{25 + box_width/2 + 5}" text-anchor="middle" font-size="11" fill="#666">is to</text>')
                x += label_width
            elif i == 1:
                # "as"
                main_svg_parts.append(f'<text x="{x + label_width/2}" y="{25 + box_width/2 + 5}" text-anchor="middle" font-size="11" font-weight="bold" fill="#333">as</text>')
                x += label_width
            elif i == 2:
                # "is to"
                main_svg_parts.append(f'<text x="{x + label_width/2}" y="{25 + box_width/2 + 5}" text-anchor="middle" font-size="11" fill="#666">is to</text>')
                x += label_width

        main_svg_parts.append('</svg>')
        main_svg = "".join(main_svg_parts)
        main_filename = f"{q_id}_main.svg"
        updates["image_url"] = save_svg(main_svg, main_filename)

    # =========================================================================
    # Generate option SVGs (these have full descriptions)
    # =========================================================================
    option_paths = []
    for i, opt in enumerate(options):
        desc = re.sub(r'^[A-E]:\s*', '', opt)
        desc_lower = desc.lower()

        svg_parts = [create_svg_header(OPTION_SIZE, OPTION_SIZE)]
        svg_parts.append('<rect width="100%" height="100%" fill="white" stroke="#ddd" rx="4"/>')

        cx, cy = OPTION_SIZE / 2, OPTION_SIZE / 2

        # Handle specific complex patterns

        # Multi-shape layouts (ana-005): "3 shapes in row/column"
        if re.search(r'\d+\s+shapes?\s+in\s+(?:a\s+)?(?:row|column)', desc_lower):
            svg_parts.append(render_multi_shape_layout(desc, OPTION_SIZE, OPTION_SIZE))

        # Side by side (ana-006): "Two triangles side by side"
        elif "side by side" in desc_lower:
            svg_parts.append(render_side_by_side_shapes(desc, OPTION_SIZE, OPTION_SIZE))

        # Frame with internal pattern (ana-007): "frame with X inside"
        elif "frame" in desc_lower and ("inside" in desc_lower or "with" in desc_lower):
            svg_parts.append(render_frame_with_internal_pattern(desc, OPTION_SIZE, OPTION_SIZE))

        # Half/semicircle shapes (ana-008)
        elif "semicircle" in desc_lower or "half circle" in desc_lower:
            parsed = parse_figure_description(desc)
            svg_parts.append(render_figure(parsed, OPTION_SIZE, OPTION_SIZE))

        elif "half square" in desc_lower:
            # Could be rectangle (half width) or triangle (diagonal cut)
            if "triangle" in desc_lower:
                svg_parts.append(draw_half_square_triangle(cx, cy, 50))
            else:
                svg_parts.append(draw_half_square(cx, cy, 50, orientation="left"))

        # Quarter square
        elif "quarter square" in desc_lower:
            svg_parts.append(draw_quarter_square(cx, cy, 60))

        # Full rectangle (wider than square)
        elif "full rectangle" in desc_lower:
            svg_parts.append(f'<rect x="20" y="30" width="60" height="40" fill="none" stroke="#333" stroke-width="2"/>')

        # Parallel lines
        elif "parallel lines" in desc_lower or "two lines" in desc_lower:
            svg_parts.append(render_parallel_lines_figure(desc, OPTION_SIZE, OPTION_SIZE))

        # Single line
        elif desc_lower.strip() == "single line" or re.match(r'^single\s+line$', desc_lower.strip()):
            svg_parts.append(draw_line(20, cy, OPTION_SIZE - 20, cy))

        # One larger shape (just a bigger shape)
        elif "larger" in desc_lower:
            parsed = parse_figure_description(desc)
            parsed["size"] = "large"
            svg_parts.append(render_figure(parsed, OPTION_SIZE, OPTION_SIZE))

        # Compound figures
        elif " on left" in desc_lower or " on right" in desc_lower or " at " in desc_lower:
            svg_parts.append(render_compound_figure(desc, OPTION_SIZE, OPTION_SIZE))

        else:
            parsed = parse_figure_description(desc)
            svg_parts.append(render_figure(parsed, OPTION_SIZE, OPTION_SIZE))

        svg_parts.append(create_svg_footer())

        filename = f"{q_id}_opt_{chr(65+i)}.svg"
        path = save_svg("".join(svg_parts), filename)
        option_paths.append(path)

    if option_paths:
        updates["images"] = option_paths

    return updates


def render_multi_shape_layout(desc: str, width: int, height: int) -> str:
    """Render multiple shapes in row or column layout."""
    desc_lower = desc.lower()
    cx, cy = width / 2, height / 2

    # Parse number of shapes
    num_match = re.search(r'(\d+)\s+shapes?', desc_lower)
    num_shapes = int(num_match.group(1)) if num_match else 3

    # Determine layout direction
    is_column = "column" in desc_lower
    is_row = "row" in desc_lower or not is_column

    # Extract shape names from description
    shapes = []
    shape_names = ["circle", "square", "triangle", "star", "hexagon", "pentagon", "diamond"]
    for name in shape_names:
        if name in desc_lower:
            shapes.append(name)

    # If we found some shapes, use them. Otherwise default
    if not shapes:
        shapes = ["circle", "square", "triangle"][:num_shapes]
    elif len(shapes) < num_shapes:
        shapes = shapes * (num_shapes // len(shapes) + 1)
        shapes = shapes[:num_shapes]

    # Determine fill
    fill = "none"
    if "black" in desc_lower:
        fill = "#333"
    elif "grey" in desc_lower or "gray" in desc_lower:
        fill = "#999"
    elif "white" in desc_lower:
        fill = "#fff"
    elif "striped" in desc_lower:
        fill = "none"  # Will need pattern for striped

    fills = [fill] * num_shapes

    if is_row:
        return draw_shapes_in_row(cx, cy, shapes, size=25, spacing=30, fills=fills)
    else:
        return draw_shapes_in_column(cx, cy, shapes, size=25, spacing=30, fills=fills)


def render_side_by_side_shapes(desc: str, width: int, height: int) -> str:
    """Render two shapes side by side."""
    desc_lower = desc.lower()
    cx, cy = width / 2, height / 2

    # Detect shape type
    shape = "triangle"
    for s in ["hexagon", "pentagon", "diamond", "square", "rectangle", "circle", "triangle", "star"]:
        if s in desc_lower:
            shape = s
            break

    # Detect count
    count = 2
    if "three" in desc_lower or "3" in desc_lower:
        count = 3

    shapes = [shape] * count
    return draw_shapes_in_row(cx, cy, shapes, size=30, spacing=35)


def render_frame_with_internal_pattern(desc: str, width: int, height: int) -> str:
    """Render shape frame with internal line pattern."""
    desc_lower = desc.lower()
    cx, cy = width / 2, height / 2
    size = 60

    # Detect outer frame shape
    frame_shape = "square"
    for s in ["hexagon", "pentagon", "diamond", "circle", "triangle", "square"]:
        if s + " frame" in desc_lower or "frame" in desc_lower and s in desc_lower:
            frame_shape = s
            break

    # Detect internal pattern
    pattern = None
    if "diagonal cross" in desc_lower or "x-shape" in desc_lower or "x inside" in desc_lower:
        pattern = "x"
    elif "plus" in desc_lower or "+ " in desc_lower or "cross" in desc_lower:
        pattern = "cross"
    elif "y-shape" in desc_lower or "y inside" in desc_lower:
        pattern = "y"
    elif "asterisk" in desc_lower or "* inside" in desc_lower:
        pattern = "asterisk"
    elif "star" in desc_lower and "inside" in desc_lower:
        # Actual star shape inside, not asterisk
        elements = []
        elements.append(draw_shape(frame_shape, cx, cy, size, fill="none", stroke="#333"))
        elements.append(draw_star(cx, cy, size * 0.3, fill="none", stroke="#333"))
        return "".join(elements)
    elif "t-shape" in desc_lower or "t inside" in desc_lower:
        pattern = "t"

    elements = []
    elements.append(draw_shape(frame_shape, cx, cy, size, fill="none", stroke="#333"))

    if pattern == "x":
        elements.append(draw_internal_x(cx, cy, size * 0.7))
    elif pattern == "cross":
        elements.append(draw_internal_cross(cx, cy, size * 0.7))
    elif pattern == "y":
        elements.append(draw_internal_y(cx, cy, size * 0.7))
    elif pattern == "asterisk":
        elements.append(draw_internal_asterisk(cx, cy, size * 0.7))
    elif pattern == "t":
        elements.append(draw_internal_t(cx, cy, size * 0.7))

    return "".join(elements)


def render_parallel_lines_figure(desc: str, width: int, height: int) -> str:
    """Render parallel lines figure."""
    desc_lower = desc.lower()
    cx, cy = width / 2, height / 2

    # Detect count
    count = 2
    if "three" in desc_lower or "3" in desc_lower:
        count = 3

    # Detect orientation
    orientation = "vertical"
    if "horizontal" in desc_lower:
        orientation = "horizontal"

    return draw_parallel_lines(cx, cy, count, length=60, spacing=15, orientation=orientation)


def generate_matrices_svgs(question: dict) -> dict:
    """Generate SVGs for nvr_matrices questions."""
    q_id = question.get("id", "mat")
    options = question["content"].get("options", [])

    updates = {}

    # Generate option SVGs
    option_paths = []
    for i, opt in enumerate(options):
        desc = re.sub(r'^[A-E]:\s*', '', opt)
        parsed = parse_figure_description(desc)

        svg_parts = [create_svg_header(OPTION_SIZE, OPTION_SIZE)]
        svg_parts.append('<rect width="100%" height="100%" fill="white" stroke="#ddd" rx="4"/>')
        svg_parts.append(render_figure(parsed, OPTION_SIZE, OPTION_SIZE))
        svg_parts.append(create_svg_footer())

        filename = f"{q_id}_opt_{chr(65+i)}.svg"
        path = save_svg("".join(svg_parts), filename)
        option_paths.append(path)

    if option_paths:
        updates["images"] = option_paths

    return updates


def generate_rotation_svgs(question: dict) -> dict:
    """Generate SVGs for nvr_rotation questions.

    Options have descriptions of rotated figures.
    """
    q_id = question.get("id", "rot")
    text = question["content"].get("text", "")
    options = question["content"].get("options", [])
    context = question["content"].get("context", {})

    updates = {}

    # =========================================================================
    # Generate main figure showing the original figure with rotation instruction
    # =========================================================================
    # Parse the original figure description from question text
    # Format: "Original: description" or text after first line break
    original_match = re.search(r'Original:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
    if original_match:
        original_desc = original_match.group(1).strip()

        # Extract rotation amount from question text
        rotation_text = ""
        rot_match = re.search(r'rotated\s+(\d+)\s*degrees?\s*(clockwise|anticlockwise|counterclockwise)?', text, re.IGNORECASE)
        if rot_match:
            degrees = rot_match.group(1)
            direction = rot_match.group(2) or "clockwise"
            rotation_text = f"Rotate {degrees} deg {direction}"

        # Layout: Original figure with instruction text
        width = 200
        height = 180

        main_svg_parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">']
        main_svg_parts.append('<rect width="100%" height="100%" fill="#f8f9fa"/>')

        # Title
        main_svg_parts.append(f'<text x="{width/2}" y="18" text-anchor="middle" font-size="12" font-weight="bold" fill="#333">ORIGINAL FIGURE</text>')

        # Figure box
        box_size = 120
        box_x = (width - box_size) / 2
        box_y = 28
        main_svg_parts.append(f'<rect x="{box_x}" y="{box_y}" width="{box_size}" height="{box_size}" fill="white" stroke="#333" stroke-width="2" rx="4"/>')

        # Render the original figure
        # Parse and render the description
        desc_lower = original_desc.lower()

        # Check for letter patterns (e.g., "Letter 'R' with...")
        letter_match = re.search(r"letter\s*['\"]?([A-Z])['\"]?", original_desc, re.IGNORECASE)
        if letter_match:
            letter = letter_match.group(1).upper()
            cx, cy = box_x + box_size/2, box_y + box_size/2
            main_svg_parts.append(draw_letter(letter, cx, cy, 50))

            # Check for marker position
            marker_match = re.search(r'(?:circle|dot|marker)\s+(?:at\s+|in\s+)?(top-right|top-left|bottom-right|bottom-left)', desc_lower)
            if marker_match:
                marker_pos = marker_match.group(1)
                margin = 15
                marker_positions = {
                    "top-left": (box_x + margin, box_y + margin),
                    "top-right": (box_x + box_size - margin, box_y + margin),
                    "bottom-left": (box_x + margin, box_y + box_size - margin),
                    "bottom-right": (box_x + box_size - margin, box_y + box_size - margin),
                }
                if marker_pos in marker_positions:
                    mx, my = marker_positions[marker_pos]
                    main_svg_parts.append(draw_shape("circle", mx, my, 12, fill="none", stroke="#333"))

        elif "t-shape" in desc_lower or "t shape" in desc_lower:
            cx, cy = box_x + box_size/2, box_y + box_size/2
            rotation = 0
            if "horizontal bar on left" in desc_lower:
                rotation = 270
            elif "horizontal bar on right" in desc_lower:
                rotation = 90
            main_svg_parts.append(draw_t_shape(cx, cy, 60, rotation))

        elif "l-shape" in desc_lower or "l shape" in desc_lower:
            cx, cy = box_x + box_size/2, box_y + box_size/2
            main_svg_parts.append(draw_l_shape(cx, cy, 60))

        elif "flag" in desc_lower:
            cx, cy = box_x + box_size/2, box_y + box_size/2
            direction = "right"
            if "pointing up" in desc_lower:
                direction = "up"
            elif "pointing down" in desc_lower:
                direction = "down"
            elif "pointing left" in desc_lower:
                direction = "left"
            main_svg_parts.append(draw_flag(cx, cy, 50, direction))

        elif "plus sign" in desc_lower or "plus" in desc_lower and "cross" in desc_lower:
            cx, cy = box_x + box_size/2, box_y + box_size/2
            main_svg_parts.append(draw_shape("cross", cx, cy, 50))
            # Check for shaded arm
            if "top arm shaded" in desc_lower or "top arm black" in desc_lower:
                main_svg_parts.append(f'<rect x="{cx - 8}" y="{cy - 25}" width="16" height="25" fill="#333"/>')

        else:
            # General figure parsing
            parsed = parse_figure_description(original_desc)
            fig_elements = render_figure(parsed, box_size, box_size)
            main_svg_parts.append(f'<g transform="translate({box_x}, {box_y})">{fig_elements}</g>')

        # Rotation instruction
        if rotation_text:
            main_svg_parts.append(f'<text x="{width/2}" y="{box_y + box_size + 22}" text-anchor="middle" font-size="12" fill="#666">{rotation_text}</text>')

        main_svg_parts.append('</svg>')
        main_svg = "".join(main_svg_parts)
        main_filename = f"{q_id}_main.svg"
        updates["image_url"] = save_svg(main_svg, main_filename)

    # =========================================================================
    # Generate option SVGs
    # =========================================================================
    option_paths = []
    for i, opt in enumerate(options):
        desc = re.sub(r'^[A-E]:\s*', '', opt)
        desc_lower = desc.lower()

        svg_parts = [create_svg_header(OPTION_SIZE, OPTION_SIZE)]
        svg_parts.append('<rect width="100%" height="100%" fill="white" stroke="#ddd" rx="4"/>')

        cx, cy = OPTION_SIZE / 2, OPTION_SIZE / 2

        # Check for letter patterns (e.g., "Upside-down R", "Normal R", "Backwards R")
        letter_match = re.search(r'\b([RLTFEPNK])\b(?:\s+with|\s*,)', desc, re.IGNORECASE)
        if not letter_match:
            letter_match = re.search(r'(upside-down|backwards|normal|rotated)\s+([RLTFEPNK])\b', desc_lower)
            if letter_match:
                letter = letter_match.group(2).upper()
            else:
                letter = None
        else:
            letter = letter_match.group(1).upper()

        # Detect marker position from description
        marker_pos = None
        marker_match = re.search(r'(?:circle|dot|marker)\s+(?:at\s+|in\s+)?(top-right|top-left|bottom-right|bottom-left)', desc_lower)
        if marker_match:
            marker_pos = marker_match.group(1)

        if letter:
            # Render letter with appropriate transformation
            rotation = 0
            mirror = False
            if "upside-down" in desc_lower:
                rotation = 180
            if "backwards" in desc_lower:
                mirror = True

            # Draw the letter (with mirror effect if needed)
            if mirror:
                svg_parts.append(f'<g transform="scale(-1, 1) translate(-100, 0)">')
                svg_parts.append(draw_letter(letter, cx, cy, 40, rotation))
                svg_parts.append('</g>')
            else:
                svg_parts.append(draw_letter(letter, cx, cy, 40, rotation))

            # Draw marker circle at position
            if marker_pos:
                marker_positions = {
                    "top-left": (15, 15),
                    "top-right": (85, 15),
                    "bottom-left": (15, 85),
                    "bottom-right": (85, 85),
                }
                if marker_pos in marker_positions:
                    mx, my = marker_positions[marker_pos]
                    svg_parts.append(draw_shape("circle", mx, my, 12, fill="none", stroke="#333"))

        elif "t-shape" in desc_lower or "t shape" in desc_lower:
            rotation = 0
            if "horizontal bar on top" in desc_lower or "bar on top" in desc_lower:
                rotation = 0
            elif "extending down" in desc_lower:
                rotation = 0
            elif "horizontal bar on left" in desc_lower:
                rotation = 270
            elif "horizontal bar on right" in desc_lower or "extending left" in desc_lower:
                rotation = 90
            elif "horizontal bar at bottom" in desc_lower or "bar at bottom" in desc_lower:
                rotation = 180
            svg_parts.append(draw_t_shape(cx, cy, 60, rotation))

        elif "l-shape" in desc_lower or "l shape" in desc_lower:
            rotation = 0
            if "vertical bar on right" in desc_lower:
                rotation = 180
            elif "horizontal bar on top" in desc_lower:
                rotation = 270
            svg_parts.append(draw_l_shape(cx, cy, 60, rotation))

        else:
            # Fall back to general figure parsing
            parsed = parse_figure_description(desc)
            svg_parts.append(render_figure(parsed, OPTION_SIZE, OPTION_SIZE))

        svg_parts.append(create_svg_footer())

        filename = f"{q_id}_opt_{chr(65+i)}.svg"
        path = save_svg("".join(svg_parts), filename)
        option_paths.append(path)

    if option_paths:
        updates["images"] = option_paths

    return updates


def generate_reflection_svgs(question: dict) -> dict:
    """Generate SVGs for nvr_reflection questions."""
    q_id = question.get("id", "ref")
    options = question["content"].get("options", [])

    updates = {}

    # Generate option SVGs
    option_paths = []
    for i, opt in enumerate(options):
        desc = re.sub(r'^[A-E]:\s*', '', opt)
        parsed = parse_figure_description(desc)

        svg_parts = [create_svg_header(OPTION_SIZE, OPTION_SIZE)]
        svg_parts.append('<rect width="100%" height="100%" fill="white" stroke="#ddd" rx="4"/>')

        # Handle L-shape variations
        if "l" in desc.lower() and ("rotated" in desc.lower() or "backwards" in desc.lower() or "upside" in desc.lower()):
            rotation = 0
            if "horizontal bar on top" in desc.lower():
                rotation = 270
            elif "vertical bar on right" in desc.lower():
                rotation = 180
            elif "horizontal bar at top" in desc.lower():
                rotation = 270
            svg_parts.append(draw_l_shape(50, 50, 60, rotation))
        else:
            svg_parts.append(render_figure(parsed, OPTION_SIZE, OPTION_SIZE))

        svg_parts.append(create_svg_footer())

        filename = f"{q_id}_opt_{chr(65+i)}.svg"
        path = save_svg("".join(svg_parts), filename)
        option_paths.append(path)

    if option_paths:
        updates["images"] = option_paths

    return updates


def generate_codes_svgs(question: dict) -> dict:
    """Generate SVGs for nvr_codes questions.

    Options are codes like "AY", "BX" etc. We need to decode them using
    the context.code_system to determine what shapes to render.
    """
    q_id = question.get("id", "cod")
    text = question["content"].get("text", "")
    options = question["content"].get("options", [])
    context = question["content"].get("context", {})
    code_system = context.get("code_system", {})

    updates = {}

    if not code_system:
        return updates

    # =========================================================================
    # Generate main figure showing the code table with example figures
    # =========================================================================
    # Parse "Fig N: description = CODE" patterns from question text
    fig_pattern = r'Fig\s*(\d+):\s*(.+?)\s*=\s*(\w+)'
    fig_matches = re.findall(fig_pattern, text)

    # Also parse the test figure: "Test figure: description = ?"
    test_pattern = r'Test\s*figure:\s*(.+?)\s*=\s*\?'
    test_match = re.search(test_pattern, text)

    if fig_matches:
        # Layout: Grid of example figures with codes, plus test figure
        num_examples = len(fig_matches)
        cols = min(num_examples, 4)  # Max 4 columns
        rows = (num_examples + cols - 1) // cols

        cell_width = 100
        cell_height = 100
        code_height = 25
        margin = 15

        total_width = cols * cell_width + (cols + 1) * margin
        total_height = rows * (cell_height + code_height) + margin * 2

        # Add space for test figure at bottom
        if test_match:
            total_height += cell_height + code_height + margin * 2
            # Add separator height
            total_height += 10

        main_svg_parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_width} {total_height}" width="{total_width}" height="{total_height}">']
        main_svg_parts.append('<rect width="100%" height="100%" fill="#f8f9fa"/>')

        # Render example figures
        for idx, (fig_num, desc, code) in enumerate(fig_matches):
            col = idx % cols
            row = idx // cols

            x = margin + col * (cell_width + margin)
            y = margin + row * (cell_height + code_height + margin)

            # Figure box
            main_svg_parts.append(f'<rect x="{x}" y="{y}" width="{cell_width - margin}" height="{cell_height - margin}" fill="white" stroke="#ddd" rx="4"/>')

            # Render figure based on description
            parsed = parse_figure_description(desc)
            fig_elements = render_figure(parsed, cell_width - margin, cell_height - margin)
            main_svg_parts.append(f'<g transform="translate({x}, {y})">{fig_elements}</g>')

            # Code label below
            label_y = y + cell_height - margin + code_height / 2 + 5
            main_svg_parts.append(f'<text x="{x + (cell_width - margin)/2}" y="{label_y}" text-anchor="middle" font-size="14" font-weight="bold" fill="#333">= {code}</text>')

        # Add test figure section
        if test_match:
            test_desc = test_match.group(1).strip()
            separator_y = margin + rows * (cell_height + code_height + margin) + 5

            # Separator line
            main_svg_parts.append(f'<line x1="{margin}" y1="{separator_y}" x2="{total_width - margin}" y2="{separator_y}" stroke="#ccc" stroke-width="1" stroke-dasharray="5,5"/>')

            # Test figure label
            test_y = separator_y + margin
            main_svg_parts.append(f'<text x="{total_width/2}" y="{test_y}" text-anchor="middle" font-size="11" fill="#666">TEST FIGURE</text>')

            # Test figure box
            test_box_x = (total_width - cell_width + margin) / 2
            test_box_y = test_y + 8
            main_svg_parts.append(f'<rect x="{test_box_x}" y="{test_box_y}" width="{cell_width - margin}" height="{cell_height - margin}" fill="white" stroke="#333" stroke-width="2" rx="4"/>')

            # Render test figure
            parsed = parse_figure_description(test_desc)
            fig_elements = render_figure(parsed, cell_width - margin, cell_height - margin)
            main_svg_parts.append(f'<g transform="translate({test_box_x}, {test_box_y})">{fig_elements}</g>')

            # Question mark for code
            code_label_y = test_box_y + cell_height - margin + code_height / 2 + 5
            main_svg_parts.append(f'<text x="{total_width/2}" y="{code_label_y}" text-anchor="middle" font-size="16" font-weight="bold" fill="#666">= ?</text>')

        main_svg_parts.append('</svg>')
        main_svg = "".join(main_svg_parts)
        main_filename = f"{q_id}_main.svg"
        updates["image_url"] = save_svg(main_svg, main_filename)

    # =========================================================================
    # Generate option SVGs
    # =========================================================================
    option_paths = []
    for i, opt in enumerate(options):
        # Extract the code (e.g., "A: AY" -> "AY")
        code = re.sub(r'^[A-E]:\s*', '', opt).strip()

        # Decode the code to figure attributes
        attrs = decode_code(code, code_system)

        svg_parts = [create_svg_header(OPTION_SIZE, OPTION_SIZE)]
        svg_parts.append('<rect width="100%" height="100%" fill="white" stroke="#ddd" rx="4"/>')

        # Render figure based on decoded attributes
        cx, cy = OPTION_SIZE / 2, OPTION_SIZE / 2
        size = get_size_value(attrs.get("size", "medium"))
        fill = get_fill_color(attrs.get("fill", "none"))
        shape = attrs.get("shape", "circle")

        # Handle direction/pointing
        rotation = 0
        if attrs.get("direction") == "pointing_up":
            rotation = 0
        elif attrs.get("direction") == "pointing_right":
            rotation = 90
        elif attrs.get("direction") == "pointing_down":
            rotation = 180
        elif attrs.get("direction") == "pointing_left":
            rotation = 270

        stroke = "#fff" if fill == "#333" else "#333"
        svg_parts.append(draw_shape(shape, cx, cy, size, fill=fill, stroke=stroke, rotation=rotation))

        # Draw dots if specified
        if attrs.get("dots"):
            svg_parts.append(draw_dots_inside(attrs["dots"], cx, cy))

        svg_parts.append(create_svg_footer())

        filename = f"{q_id}_opt_{chr(65+i)}.svg"
        path = save_svg("".join(svg_parts), filename)
        option_paths.append(path)

    if option_paths:
        updates["images"] = option_paths

    return updates


def decode_code(code: str, code_system: dict) -> dict:
    """Decode a letter code into figure attributes."""
    attrs = {}

    # Process each position in the code
    for pos, (key, mappings) in enumerate(code_system.items()):
        if pos < len(code):
            letter = code[pos]
            if letter in mappings:
                value = mappings[letter]
                # Determine the attribute type from the key name
                if "size" in key.lower() or key == "first_letter":
                    attrs["size"] = value
                elif "fill" in key.lower() or "color" in key.lower() or key == "second_letter":
                    attrs["fill"] = value
                elif "shape" in key.lower():
                    attrs["shape"] = value
                elif "direction" in key.lower() or key == "third_letter":
                    attrs["direction"] = value
                elif "dot" in key.lower():
                    attrs["dots"] = int(value) if value.isdigit() else 0

    return attrs


# =============================================================================
# SPATIAL 3D HELPER FUNCTIONS FOR MAIN FIGURES
# =============================================================================

def generate_cube_faces_main_figure(q_id: str, text: str, initial_state: dict) -> str:
    """Generate main figure showing a cube with labeled faces."""
    width = 200
    height = 180

    svg_parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">']
    svg_parts.append('<rect width="100%" height="100%" fill="#f8f9fa"/>')

    # Draw an isometric-style cube representation
    cx, cy = 100, 90
    face_size = 50

    # Draw 3 visible faces of a cube (top, front, right) in isometric view
    # Front face (square)
    front_x, front_y = cx - 30, cy
    svg_parts.append(f'<rect x="{front_x}" y="{front_y}" width="{face_size}" height="{face_size}" fill="#e8e8e8" stroke="#333" stroke-width="2"/>')

    # Right face (parallelogram)
    right_pts = f"{front_x + face_size},{front_y} {front_x + face_size + 25},{front_y - 20} {front_x + face_size + 25},{front_y + face_size - 20} {front_x + face_size},{front_y + face_size}"
    svg_parts.append(f'<polygon points="{right_pts}" fill="#d0d0d0" stroke="#333" stroke-width="2"/>')

    # Top face (parallelogram)
    top_pts = f"{front_x},{front_y} {front_x + 25},{front_y - 20} {front_x + face_size + 25},{front_y - 20} {front_x + face_size},{front_y}"
    svg_parts.append(f'<polygon points="{top_pts}" fill="#f0f0f0" stroke="#333" stroke-width="2"/>')

    # Add labels for faces from initial_state
    label_positions = {
        "top": (front_x + 25 + face_size/2 - 5, front_y - 10),
        "front": (front_x + face_size/2, front_y + face_size/2 + 5),
        "right": (front_x + face_size + 12, front_y + face_size/2 - 10),
    }

    shape_symbols = {
        "star": "*",
        "circle": "O",
        "triangle": "/\\",
        "square": "[]",
    }

    for face, (lx, ly) in label_positions.items():
        if face in initial_state:
            symbol = initial_state[face]
            display = shape_symbols.get(symbol.lower(), symbol[:3].upper())
            svg_parts.append(f'<text x="{lx}" y="{ly}" text-anchor="middle" font-size="11" fill="#333">{display}</text>')

    # Add title
    svg_parts.append(f'<text x="{width/2}" y="20" text-anchor="middle" font-size="11" fill="#666">CUBE FACES</text>')

    # Add legend
    legend_y = 160
    legend_items = []
    for face, value in initial_state.items():
        legend_items.append(f"{face.upper()}={value}")
    if legend_items:
        svg_parts.append(f'<text x="{width/2}" y="{legend_y}" text-anchor="middle" font-size="10" fill="#666">{", ".join(legend_items)}</text>')

    svg_parts.append('</svg>')
    main_svg = "".join(svg_parts)
    filename = f"{q_id}_main.svg"
    return save_svg(main_svg, filename)


def generate_net_main_figure(q_id: str, text: str, context: dict) -> str:
    """Generate main figure showing a cube net layout."""
    width = 220
    height = 200

    svg_parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">']
    svg_parts.append('<rect width="100%" height="100%" fill="#f8f9fa"/>')

    # Draw a cross-shaped net
    cell_size = 40
    cx, cy = width / 2, height / 2

    # Net positions for cross shape:
    #       [A]
    # [B] [STAR] [C] [D]
    #       [E]
    positions = [
        (cx - cell_size/2, cy - cell_size * 1.5),  # A - top
        (cx - cell_size * 1.5, cy - cell_size/2),  # B - left
        (cx - cell_size/2, cy - cell_size/2),      # STAR - center
        (cx + cell_size/2, cy - cell_size/2),      # C - right
        (cx + cell_size * 1.5, cy - cell_size/2),  # D - far right
        (cx - cell_size/2, cy + cell_size/2),      # E - bottom
    ]

    labels = ['A', 'B', '*', 'C', 'D', 'E']

    for (x, y), label in zip(positions, labels):
        # Draw cell
        fill = "#ffffcc" if label == '*' else "white"
        svg_parts.append(f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" fill="{fill}" stroke="#333" stroke-width="2"/>')
        # Draw label
        if label == '*':
            svg_parts.append(draw_star(x + cell_size/2, y + cell_size/2, 12, fill="none", stroke="#333"))
        else:
            svg_parts.append(f'<text x="{x + cell_size/2}" y="{y + cell_size/2 + 5}" text-anchor="middle" font-size="14" font-weight="bold" fill="#333">{label}</text>')

    # Title
    svg_parts.append(f'<text x="{width/2}" y="20" text-anchor="middle" font-size="11" fill="#666">CUBE NET</text>')

    svg_parts.append('</svg>')
    main_svg = "".join(svg_parts)
    filename = f"{q_id}_main.svg"
    return save_svg(main_svg, filename)


def generate_staircase_main_figure(q_id: str, text: str, layers: list) -> str:
    """Generate main figure showing a 3D staircase structure."""
    width = 200
    height = 180

    svg_parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">']
    svg_parts.append('<rect width="100%" height="100%" fill="#f8f9fa"/>')

    # Default to 3-step staircase if no layers provided
    if not layers:
        layers = [3, 2, 1]

    # Draw isometric staircase
    cube_w = 25  # width of each unit cube face
    cube_h = 20  # height of each unit cube face
    iso_offset = 12  # isometric offset

    start_x = 50
    start_y = 140

    for layer_idx, num_cubes in enumerate(layers):
        for cube_idx in range(num_cubes):
            # Calculate position
            x = start_x + cube_idx * cube_w + layer_idx * iso_offset
            y = start_y - layer_idx * cube_h - cube_idx * 0

            # Draw front face
            svg_parts.append(f'<rect x="{x}" y="{y - cube_h}" width="{cube_w}" height="{cube_h}" fill="#e8e8e8" stroke="#333" stroke-width="1"/>')

            # Draw top face
            top_pts = f"{x},{y - cube_h} {x + iso_offset},{y - cube_h - 8} {x + cube_w + iso_offset},{y - cube_h - 8} {x + cube_w},{y - cube_h}"
            svg_parts.append(f'<polygon points="{top_pts}" fill="#f8f8f8" stroke="#333" stroke-width="1"/>')

            # Draw right face (only for rightmost cube in each layer)
            if cube_idx == num_cubes - 1:
                right_pts = f"{x + cube_w},{y - cube_h} {x + cube_w + iso_offset},{y - cube_h - 8} {x + cube_w + iso_offset},{y - 8} {x + cube_w},{y}"
                svg_parts.append(f'<polygon points="{right_pts}" fill="#d0d0d0" stroke="#333" stroke-width="1"/>')

    # Title
    svg_parts.append(f'<text x="{width/2}" y="20" text-anchor="middle" font-size="11" fill="#666">3D STRUCTURE</text>')

    # Layer info
    total = sum(layers)
    svg_parts.append(f'<text x="{width/2}" y="170" text-anchor="middle" font-size="10" fill="#666">Layers: {" + ".join(map(str, layers))} = ?</text>')

    svg_parts.append('</svg>')
    main_svg = "".join(svg_parts)
    filename = f"{q_id}_main.svg"
    return save_svg(main_svg, filename)


def generate_painted_cube_main_figure(q_id: str, text: str, context: dict) -> str:
    """Generate main figure showing a painted cube being cut."""
    width = 220
    height = 180

    svg_parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">']
    svg_parts.append('<rect width="100%" height="100%" fill="#f8f9fa"/>')

    # Draw a cube with grid lines showing the cut pattern
    cx, cy = 110, 90
    size = 60

    # Front face with grid
    front_x, front_y = cx - 35, cy - 10
    svg_parts.append(f'<rect x="{front_x}" y="{front_y}" width="{size}" height="{size}" fill="#ffcccc" stroke="#c00" stroke-width="2"/>')

    # Grid lines for 3x3 cut
    for i in range(1, 3):
        # Vertical lines
        svg_parts.append(f'<line x1="{front_x + i * size/3}" y1="{front_y}" x2="{front_x + i * size/3}" y2="{front_y + size}" stroke="#999" stroke-width="1" stroke-dasharray="3,2"/>')
        # Horizontal lines
        svg_parts.append(f'<line x1="{front_x}" y1="{front_y + i * size/3}" x2="{front_x + size}" y2="{front_y + i * size/3}" stroke="#999" stroke-width="1" stroke-dasharray="3,2"/>')

    # Right face
    right_pts = f"{front_x + size},{front_y} {front_x + size + 20},{front_y - 15} {front_x + size + 20},{front_y + size - 15} {front_x + size},{front_y + size}"
    svg_parts.append(f'<polygon points="{right_pts}" fill="#ffaaaa" stroke="#c00" stroke-width="2"/>')

    # Top face
    top_pts = f"{front_x},{front_y} {front_x + 20},{front_y - 15} {front_x + size + 20},{front_y - 15} {front_x + size},{front_y}"
    svg_parts.append(f'<polygon points="{top_pts}" fill="#ffdddd" stroke="#c00" stroke-width="2"/>')

    # Title
    svg_parts.append(f'<text x="{width/2}" y="18" text-anchor="middle" font-size="11" fill="#666">PAINTED CUBE (cut into 3x3x3)</text>')

    # Legend
    svg_parts.append(f'<text x="{width/2}" y="165" text-anchor="middle" font-size="9" fill="#666">Red = painted faces</text>')

    svg_parts.append('</svg>')
    main_svg = "".join(svg_parts)
    filename = f"{q_id}_main.svg"
    return save_svg(main_svg, filename)


def generate_spatial_3d_svgs(question: dict) -> dict:
    """Generate SVGs for nvr_spatial_3d questions.

    Options are abstract (e.g., "Face D", "Star", "The shape that was on BOTTOM").
    We render simple 2D representations based on context.
    """
    q_id = question.get("id", "3d")
    text = question["content"].get("text", "")
    options = question["content"].get("options", [])
    context = question["content"].get("context", {})

    updates = {}

    # =========================================================================
    # Generate main figure showing the 3D scenario
    # =========================================================================
    text_lower = text.lower()

    # Determine the type of 3D question
    if "net" in text_lower and ("fold" in text_lower or "cube" in text_lower):
        # Net folding question - show the net layout
        updates["image_url"] = generate_net_main_figure(q_id, text, context)

    elif "cube" in text_lower and "faces" in text_lower:
        # Cube with labeled faces
        initial_state = context.get("initial_state", {})
        updates["image_url"] = generate_cube_faces_main_figure(q_id, text, initial_state)

    elif "unit cube" in text_lower or "staircase" in text_lower or "3d shape" in text_lower:
        # Cube counting / staircase
        layers = context.get("layers", [])
        updates["image_url"] = generate_staircase_main_figure(q_id, text, layers)

    elif "painted" in text_lower and "cut" in text_lower:
        # Painted cube being cut
        updates["image_url"] = generate_painted_cube_main_figure(q_id, text, context)

    else:
        # Default: Try to extract info from text and context
        initial_state = context.get("initial_state", {})
        if initial_state:
            updates["image_url"] = generate_cube_faces_main_figure(q_id, text, initial_state)

    # =========================================================================
    # Generate option SVGs
    # =========================================================================
    option_paths = []
    for i, opt in enumerate(options):
        desc = re.sub(r'^[A-E]:\s*', '', opt).strip()

        svg_parts = [create_svg_header(OPTION_SIZE, OPTION_SIZE)]
        svg_parts.append('<rect width="100%" height="100%" fill="white" stroke="#ddd" rx="4"/>')

        cx, cy = OPTION_SIZE / 2, OPTION_SIZE / 2

        # Parse what type of visual to render
        desc_lower = desc.lower()

        if "face" in desc_lower:
            # Render a labeled square face
            letter_match = re.search(r'face\s+([a-e])', desc_lower)
            if letter_match:
                label = letter_match.group(1).upper()
                svg_parts.append(draw_shape("square", cx, cy, 60, fill="#f0f0f0", stroke="#333"))
                svg_parts.append(f'<text x="{cx}" y="{cy + 8}" text-anchor="middle" font-size="24" fill="#333">{label}</text>')
        elif "star" in desc_lower:
            svg_parts.append(draw_star(cx, cy, 30, fill="none", stroke="#333"))
        elif "circle" in desc_lower:
            svg_parts.append(draw_shape("circle", cx, cy, 50, fill="none", stroke="#333"))
        elif "triangle" in desc_lower:
            svg_parts.append(draw_shape("triangle", cx, cy, 50, fill="none", stroke="#333"))
        elif "square" in desc_lower:
            svg_parts.append(draw_shape("square", cx, cy, 50, fill="none", stroke="#333"))
        elif "bottom" in desc_lower or "top" in desc_lower:
            # Render a generic cube face indicator
            svg_parts.append(draw_shape("square", cx, cy, 60, fill="#e8e8e8", stroke="#333"))
            label = "?"
            if "bottom" in desc_lower:
                label = "BTM"
            elif "top" in desc_lower:
                label = "TOP"
            svg_parts.append(f'<text x="{cx}" y="{cy + 6}" text-anchor="middle" font-size="14" fill="#666">{label}</text>')
        elif re.match(r'^\d+$', desc):
            # Just a number - render it in a box
            svg_parts.append(draw_shape("square", cx, cy, 60, fill="#f8f8f8", stroke="#333"))
            svg_parts.append(f'<text x="{cx}" y="{cy + 10}" text-anchor="middle" font-size="28" fill="#333">{desc}</text>')
        elif "new shape" in desc_lower or "unknown" in desc_lower:
            svg_parts.append(draw_shape("square", cx, cy, 60, fill="#f8f8f8", stroke="#999", stroke_width=1))
            svg_parts.append(f'<text x="{cx}" y="{cy + 8}" text-anchor="middle" font-size="24" fill="#999">?</text>')
        else:
            # Default: show the text
            # Wrap long text
            words = desc.split()
            if len(words) <= 3:
                svg_parts.append(f'<text x="{cx}" y="{cy + 6}" text-anchor="middle" font-size="12" fill="#333">{desc}</text>')
            else:
                mid = len(words) // 2
                line1 = " ".join(words[:mid])
                line2 = " ".join(words[mid:])
                svg_parts.append(f'<text x="{cx}" y="{cy - 6}" text-anchor="middle" font-size="11" fill="#333">{line1}</text>')
                svg_parts.append(f'<text x="{cx}" y="{cy + 12}" text-anchor="middle" font-size="11" fill="#333">{line2}</text>')

        svg_parts.append(create_svg_footer())

        filename = f"{q_id}_opt_{chr(65+i)}.svg"
        path = save_svg("".join(svg_parts), filename)
        option_paths.append(path)

    if option_paths:
        updates["images"] = option_paths

    return updates


# =============================================================================
# MAIN PROCESSING
# =============================================================================

def save_svg(svg_content: str, filename: str) -> str:
    """Save SVG content to file and return the relative path."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = OUTPUT_DIR / filename
    with open(filepath, "w") as f:
        f.write(svg_content)
    return f"/images/nvr/{filename}"


def process_question(question: dict) -> dict:
    """Process a question and generate its SVG images based on type."""
    q_type = question["question_type"]

    if q_type == "nvr_sequences":
        return generate_sequences_svgs(question)
    elif q_type == "nvr_odd_one_out":
        return generate_odd_one_out_svgs(question)
    elif q_type == "nvr_analogies":
        return generate_analogies_svgs(question)
    elif q_type == "nvr_matrices":
        return generate_matrices_svgs(question)
    elif q_type == "nvr_rotation":
        return generate_rotation_svgs(question)
    elif q_type == "nvr_reflection":
        return generate_reflection_svgs(question)
    elif q_type == "nvr_codes":
        return generate_codes_svgs(question)
    elif q_type == "nvr_spatial_3d":
        return generate_spatial_3d_svgs(question)
    else:
        return {}


def main():
    """Main function to generate all NVR SVGs."""
    print(f"Loading questions from {QUESTIONS_FILE}")

    with open(QUESTIONS_FILE) as f:
        questions = json.load(f)

    print(f"Processing {len(questions)} NVR questions...")

    # Count by type
    type_counts = {}
    for q in questions:
        t = q["question_type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    print("\nQuestion types found:")
    for t, count in sorted(type_counts.items()):
        print(f"  {t}: {count}")

    updated_count = 0
    errors = []

    for q in questions:
        try:
            updates = process_question(q)
            if updates:
                if "image_url" in updates:
                    q["content"]["image_url"] = updates["image_url"]
                if "images" in updates:
                    q["content"]["images"] = updates["images"]
                updated_count += 1
                print(f"  Generated SVGs for {q.get('id', 'unknown')}: {q['question_type']}")
        except Exception as e:
            errors.append((q.get('id', 'unknown'), str(e)))
            print(f"  ERROR processing {q.get('id', 'unknown')}: {e}")

    # Save updated questions
    print(f"\nSaving updated questions to {QUESTIONS_FILE}")
    with open(QUESTIONS_FILE, "w") as f:
        json.dump(questions, f, indent=2)

    print(f"\nDone! Updated {updated_count} questions with SVG images.")
    print(f"SVG files saved to {OUTPUT_DIR}")

    if errors:
        print(f"\nErrors encountered ({len(errors)}):")
        for qid, err in errors:
            print(f"  {qid}: {err}")


if __name__ == "__main__":
    main()
