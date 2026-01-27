#!/usr/bin/env python3
"""
DeepTutor Content Generator (CGP Mimic)
Generates high-fidelity 11+ questions with procedural assets.
"""

import asyncio
import json
import logging
import random
import math
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Ensure backend directory is in python path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.database import async_session, init_db
from app.db.models import QuestionDB
from sqlalchemy import text as sa_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Output dir for generated images
PUBLIC_DIR = Path(__file__).parent.parent.parent / "frontend" / "public" / "questions" / "generated"
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================
# SVG DRAWING PRIMITIVES
# ==========================================

def svg_header(w=100, h=100) -> str:
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">'

def svg_footer() -> str:
    return '</svg>'

def draw_shape(shape_type: str, cx: float, cy: float, size: float, fill: str = "none", stroke: str = "black", stroke_width: int = 2, rotation: int = 0) -> str:
    """Draw a primitive shape at (cx, cy) with rotation."""
    
    transform = f'transform="rotate({rotation}, {cx}, {cy})"'
    
    if shape_type == "circle":
        r = size / 2
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" />'
    
    elif shape_type == "square":
        x = cx - size / 2
        y = cy - size / 2
        return f'<rect x="{x}" y="{y}" width="{size}" height="{size}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" {transform} />'
    
    elif shape_type == "triangle":
        # Equilateral triangle pointing up
        h = size * (math.sqrt(3)/2)
        p1 = f"{cx},{cy - h/2}"
        p2 = f"{cx - size/2},{cy + h/2}"
        p3 = f"{cx + size/2},{cy + h/2}"
        return f'<polygon points="{p1} {p2} {p3}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" {transform} />'
    
    elif shape_type == "cross":
        path = f"M {cx-size/2} {cy} L {cx+size/2} {cy} M {cx} {cy-size/2} L {cx} {cy+size/2}"
        return f'<path d="{path}" stroke="{stroke}" stroke-width="{stroke_width}" {transform} />'
        
    elif shape_type == "star":
        # 5 point star
        points = []
        outer_r = size / 2
        inner_r = size / 4
        for i in range(10):
            angle = math.radians(i * 36 - 90) # Start top
            r = outer_r if i % 2 == 0 else inner_r
            px = cx + math.cos(angle) * r
            py = cy + math.sin(angle) * r
            points.append(f"{px},{py}")
        return f'<polygon points="{" ".join(points)}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" {transform} />'

    elif shape_type == "arrow":
        # Simple arrow pointing Right
        # We rotate it for other directions
        w = size
        h = size / 3
        path = f"M {cx-w/2} {cy} L {cx+w/2} {cy} M {cx+w/6} {cy-h} L {cx+w/2} {cy} L {cx+w/6} {cy+h}"
        return f'<path d="{path}" stroke="{stroke}" stroke-width="{stroke_width}" fill="none" {transform} />'

    return ""

# ==========================================
# NVR: MATRIX GENERATOR (3x3)
# ==========================================

def generate_matrix_svg(grid: List[Dict], filename: str) -> str:
    """
    Generates a 3x3 matrix image (with the 9th cell empty/question mark).
    grid: List of 9 dicts describing shapes.
    """
    cell_size = 100
    gap = 10
    total_w = (cell_size * 3) + (gap * 2)
    total_h = (cell_size * 3) + (gap * 2)
    
    svg = svg_header(total_w, total_h)
    
    # Draw Background Grid (lines)
    # svg += f'<rect width="100%" height="100%" fill="white" />'
    
    for i, cell in enumerate(grid):
        row = i // 3
        col = i % 3
        
        cx = (col * (cell_size + gap)) + cell_size/2
        cy = (row * (cell_size + gap)) + cell_size/2
        
        # Draw Cell Border
        # svg += f'<rect x="{cx - cell_size/2}" y="{cy - cell_size/2}" width="{cell_size}" height="{cell_size}" fill="none" stroke="#ddd" />'
        
        if i == 8: # The Missing Piece
            svg += f'<text x="{cx}" y="{cy+10}" font-family="Arial" font-size="40" text-anchor="middle" fill="#ccc">?</text>'
            continue
            
        # Draw Shape
        shape = cell.get("shape", "circle")
        fill = cell.get("fill", "none")
        rot = cell.get("rotation", 0)
        size = cell.get("size", 60)
        stroke_width = cell.get("stroke_width", 3)
        
        svg += draw_shape(shape, cx, cy, size, fill=fill, rotation=rot, stroke_width=stroke_width)
        
    svg += svg_footer()
    
    # Save
    filepath = PUBLIC_DIR / filename
    with open(filepath, "w") as f:
        f.write(svg)
        
    return f"/questions/generated/{filename}"

def generate_option_svg(cell: Dict, filename: str) -> str:
    """Generates a single option image."""
    s = 100
    svg = svg_header(s, s)
    cx, cy = s/2, s/2
    
    shape = cell.get("shape", "circle")
    fill = cell.get("fill", "none")
    rot = cell.get("rotation", 0)
    size = cell.get("size", 60)
    stroke_width = cell.get("stroke_width", 3)
    
    svg += draw_shape(shape, cx, cy, size, fill=fill, rotation=rot, stroke_width=stroke_width)
    svg += svg_footer()
    
    filepath = PUBLIC_DIR / filename
    with open(filepath, "w") as f:
        f.write(svg)
    return f"/questions/generated/{filename}"

def create_nvr_rotation_question(q_idx: int) -> Dict:
    """Create a 3x3 matrix where shapes rotate across rows."""
    base_shape = random.choice(["arrow", "triangle", "cross"])
    
    # Logic: Rotate +90 degrees each step
    grid = []
    for i in range(9):
        # row logic
        row_offset = (i // 3) * 45 # Each row starts at different base rotation?
        rotation = (row_offset + (i % 3) * 90) % 360
        
        grid.append({
            "shape": base_shape,
            "rotation": rotation,
            "fill": "none"
        })
        
    correct_cell = grid[8]
    
    # Options (1 correct, 3 distractors)
    options_data = []
    # Correct
    options_data.append(correct_cell)
    # Distractor 1
    options_data.append({**correct_cell, "rotation": (correct_cell["rotation"] + 180) % 360})
    # Distractor 2
    options_data.append({**correct_cell, "shape": "circle"})
    # Distractor 3
    options_data.append({**correct_cell, "rotation": (correct_cell["rotation"] + 90) % 360})
    # Distractor 4 (New for 5 options)
    options_data.append({**correct_cell, "shape": "cross", "rotation": 45})
    
    random.shuffle(options_data)
    correct_idx = options_data.index(correct_cell)
    
    # Generate Images
    main_img = generate_matrix_svg(grid, f"nvr_q{q_idx}_main.svg")
    opt_imgs = []
    for j, opt in enumerate(options_data):
        opt_imgs.append(generate_option_svg(opt, f"nvr_q{q_idx}_opt{j}.svg"))
        
    return {
        "subject": "non_verbal_reasoning",
        "question_type": "nvr_matrices",
        "difficulty": 4,
        "content": {
            "text": "Which option completes the pattern used in the matrix above?",
            "images": [main_img], 
            "options": ["A", "B", "C", "D", "E"], # 5 Options
            "option_images": opt_imgs 
        },
        "answer": {
            "value": "Answer",
            "correct_index": correct_idx
        },
        "source": "DeepTutor AI Engine"
    }

def create_nvr_progression_question(q_idx: int) -> Dict:
    """Create a 3x3 matrix where shape sides increase."""
    shapes = ["circle", "triangle", "square", "star"] 
    fills = ["none", "black", "#ccc"] 
    
    grid = []
    for i in range(9):
        row = i // 3
        col = i % 3
        shape = shapes[row % len(shapes)]
        fill = fills[col % len(fills)]
        
        grid.append({
            "shape": shape,
            "fill": fill,
            "rotation": 0
        })
        
    correct_cell = grid[8]
    
    options_data = []
    options_data.append(correct_cell)
    options_data.append({**correct_cell, "fill": fills[(correct_cell["fill"] != fills[0]) and 0 or 1]})
    options_data.append({**correct_cell, "shape": shapes[(shapes.index(correct_cell["shape"]) + 1) % len(shapes)]})
    options_data.append({**correct_cell, "shape": shapes[0], "fill": fills[0]})
    # Distractor 4
    options_data.append({**correct_cell, "shape": "arrow", "rotation": 90})

    random.shuffle(options_data)
    correct_idx = options_data.index(correct_cell)

    main_img = generate_matrix_svg(grid, f"nvr_q{q_idx}_main.svg")
    opt_imgs = []
    for j, opt in enumerate(options_data):
        opt_imgs.append(generate_option_svg(opt, f"nvr_q{q_idx}_opt{j}.svg"))
        
    return {
        "subject": "non_verbal_reasoning",
        "question_type": "nvr_matrices",
        "difficulty": 4,
        "content": {
            "text": "Which option completes the grid following the logic of rows and columns?",
            "images": [main_img],
            "options": ["A", "B", "C", "D", "E"],
            "option_images": opt_imgs
        },
        "answer": {
            "value": "Answer",
            "correct_index": correct_idx
        },
        "source": "DeepTutor AI Engine"
    }

# ==========================================
# MATHS: WORD PROBLEMS
# ==========================================

def generate_maths_questions() -> List[Dict]:
    qs = []
    
    # Q1: Time Difference
    qs.append({
        "subject": "maths",
        "question_type": "number_operations",
        "difficulty": 3,
        "content": {
            "text": "A train leaves London at 08:30 and arrives in Manchester at 10:15. The return journey takes 15 minutes longer. How long is the return journey?",
            "options": ["1 hr 45 mins", "2 hr 00 mins", "2 hr 15 mins", "1 hr 30 mins", "2 hr 10 mins"],
            "images": []
        },
        "answer": {"value": "2 hr 00 mins", "correct_index": 1},
        "source": "DeepTutor AI"
    })
    
    # Q2: Complex Data Table
    qs.append({
        "subject": "maths",
        "question_type": "data_handling",
        "difficulty": 4,
        "content": {
            "text": "The table below shows the cost of hiring a bike.\n\n| Time | Cost |\n|---|---|\n| First Hour | £5.00 |\n| Each extra 30 mins | £1.50 |\n\nJames hires a bike for 3 hours. How much does he pay?",
            "options": ["£9.50", "£11.00", "£12.50", "£10.00", "£11.50"],
            "images": [] 
        },
        "answer": {"value": "£11.00", "correct_index": 1},
        "explanation": "3 hours = 1st hour (£5) + 4 x 30mins (4 x £1.50 = £6). Total = £11.",
        "source": "DeepTutor AI"
    })
    
    return qs

def generate_english_questions() -> List[Dict]:
    qs = []
    # Harder vocab
    qs.append({
        "subject": "english",
        "question_type": "comprehension",
        "difficulty": 5,
        "content": {
            "text": "In the sentence 'The captain's countenance was grim as he surveyed the horizon', what does 'countenance' mean?",
            "options": ["Expression", "Ship", "Map", "Voice", "Mood"],
            "images": []
        },
        "answer": {"value": "Expression", "correct_index": 0},
        "source": "DeepTutor AI"
    })
    return qs

# ==========================================
# CGP REPLICATION (GROUND TRUTH)
# ==========================================

def create_cgp_maths_graph_question(q_idx: int) -> Dict:
    """
    Replication of CGP Maths Sample Q: Misleading Bar Chart.
    A bar chart showing 'Favorite Pets' or 'Chips' where the Y-axis doesn't start at 0.
    """
    # Logic: Bars look huge differences but are actually small.
    return {
        "subject": "maths",
        "question_type": "data_handling",
        "difficulty": 4,
        "content": {
            "text": "A chip shop records how many people had salt or vinegar on their chips.\nThe bar chart shows the results. Why is the bar chart misleading?",
            "options": [
                "The bars are different colours",
                "The numbers don't add up to 100",
                "The Y-axis does not start at 0",
                "It should be a pie chart",
                "The labels are too small"
            ],
            # Minimal ASCII rep or placeholder for the graph visual if we can't gen it yet
            "images": ["/questions/generated/maths_graph_misleading.svg"] 
        },
        "answer": {"value": "The Y-axis does not start at 0", "correct_index": 2},
        "explanation": "The vertical axis starts at 40 (or similar), which exaggerates the difference between the bars. A fair graph should start at 0.",
        "source": "CGP Replication"
    }

def create_cgp_nvr_shield_question(q_idx: int) -> Dict:
    """
    Replication of CGP NVR Sample Q: Shield Matrix.
    Logic: Outer shield rotates 90deg, Inner symbol changes.
    """
    # SVG Generator for Shield will be needed, for now we use our Matrix Gen
    # with a specific 'shield' shape if possible, or simulate it.
    
    # Let's generate a specific Matrix for this.
    # Row 1: Up-Shield, Right-Shield, Down-Shield (Rotation)
    # Row 2: Right-Shield, Down-Shield, Left-Shield
    # Row 3: Down-Shield, Left-Shield, ? (Answer: Up-Shield)
    
    grid = []
    # Simplified Logic for 'Shield' using 'triangle' for now effectively
    shapes = ["triangle"] 
    rotations = [0, 90, 180, 90, 180, 270, 180, 270] # Last is ? -> 0 (360)
    
    for i in range(8):
        grid.append({"shape": "triangle", "rotation": rotations[i], "fill": "none", "size": 70})
    
    # The missing piece (Index 8) should be Rotation 0 (Up)
    correct_cell = {"shape": "triangle", "rotation": 0, "fill": "none", "size": 70}
    
    # Options
    options_data = []
    options_data.append(correct_cell) # A (Correct)
    options_data.append({"shape": "triangle", "rotation": 90, "fill": "none", "size": 70}) # B (Wrong Rot)
    options_data.append({"shape": "triangle", "rotation": 180, "fill": "none", "size": 70}) # C (Wrong Rot)
    options_data.append({"shape": "triangle", "rotation": 270, "fill": "none", "size": 70}) # D (Wrong Rot)
    options_data.append({"shape": "circle", "rotation": 0, "fill": "none", "size": 70}) # E (Wrong Shape)

    random.shuffle(options_data)
    correct_idx = options_data.index(correct_cell)

    main_img = generate_matrix_svg(grid + [correct_cell], f"nvr_cgp_shield_{q_idx}.svg")
    opt_imgs = [generate_option_svg(opt, f"nvr_cgp_shield_opt{j}.svg") for j, opt in enumerate(options_data)]
    
    return {
        "subject": "non_verbal_reasoning",
        "question_type": "nvr_matrices",
        "difficulty": 4,
        "content": {
            "text": "Which option completes the matrix? (Shield Pattern)",
            "images": [main_img],
            "options": ["A", "B", "C", "D", "E"],
            "option_images": opt_imgs
        },
        "answer": {"value": "Answer", "correct_index": correct_idx},
        "explanation": "The shield rotates 90 degrees clockwise in each step across the row.",
        "source": "CGP Replication"
    }

def create_nvr_complex_progression(q_idx: int) -> Dict:
    """
    Expert Level: 2-Variable Logic (Shape AND Fill change).
    Row Logic: Shape stays same, Fill pattern: White -> Black -> Striped.
    """
    shapes = ["star", "cross", "diamond", "hexagon"] # Need support for these or map to existing
    # Mapping to supported: star, cross, square
    base_shapes = ["star", "cross", "square"]
    
    fills = ["none", "black", "#ccc"] # White, Black, Grey (proxy for striped)
    
    grid = []
    # R1: Star(W) -> Star(B) -> Star(G)
    # R2: Cross(W) -> Cross(B) -> Cross(G)
    # R3: Square(W) -> Square(B) -> ? (Square G)
    
    target_shape = base_shapes[2] # Square
    target_fill = fills[2] # Grey
    
    for row in range(3):
        r_shape = base_shapes[row]
        for col in range(3):
            c_fill = fills[col]
            grid.append({
                "shape": r_shape,
                "fill": c_fill,
                "rotation": 0,
                "size": 60 + (col * 5) # Slight size increase too for extra complexity
            })
            
    correct_cell = grid[8]
    
    # Options (Double Variable Distractors)
    options_data = []
    options_data.append(correct_cell) # A: Correct (Square, Grey)
    options_data.append({**correct_cell, "fill": fills[1]}) # B: Wrong Fill (Black)
    options_data.append({**correct_cell, "shape": base_shapes[1]}) # C: Wrong Shape (Cross)
    options_data.append({**correct_cell, "shape": "circle"}) # D: Random Shape
    options_data.append({**correct_cell, "fill": fills[0]}) # E: Wrong Fill (White)
    
    random.shuffle(options_data)
    correct_idx = options_data.index(correct_cell)
    
    main_img = generate_matrix_svg(grid, f"nvr_complex_q{q_idx}.svg")
    opt_imgs = [generate_option_svg(opt, f"nvr_complex_q{q_idx}_opt{j}.svg") for j, opt in enumerate(options_data)]
    
    return {
        "subject": "non_verbal_reasoning",
        "question_type": "nvr_matrices",
        "difficulty": 5,
        "content": {
            "text": "Which option completes the matrix? (Look for two changing rules)",
            "images": [main_img],
            "options": ["A", "B", "C", "D", "E"],
            "option_images": opt_imgs
        },
        "answer": {"value": "Answer", "correct_index": correct_idx},
        "explanation": "Two rules apply: 1. The shape is constant across rows. 2. The fill changes White -> Black -> Grey across columns.",
        "source": "DeepTutor Expert AI"
    }

async def main():
    await init_db()
    # await clear_database() 
    
    all_qs = []
    
    # 1. CGP REPLICATIONS (The Ground Truths)
    logger.info("Generating CGP Ground Truths...")
    all_qs.append(create_cgp_maths_graph_question(0))
    all_qs.append(create_cgp_nvr_shield_question(0))
    
    # 2. EXPERT LEVEL CONTENT
    logger.info("Generating Expert NVR...")
    for i in range(5):
        all_qs.append(create_nvr_complex_progression(i))
    
    # 3. General Procedural Content
    logger.info("Generating Standard NVR...")
    for i in range(5):
        if i % 2 == 0:
            all_qs.append(create_nvr_rotation_question(i))
        else:
            all_qs.append(create_nvr_progression_question(i))
            
    logger.info("Generating Maths & English...")
    all_qs.extend(generate_maths_questions())
    all_qs.extend(generate_english_questions())
    
    logger.info(f"Ingesting {len(all_qs)} questions...")
    
    async with async_session() as session:
        for q in all_qs:
            db_q = QuestionDB(
                subject=q["subject"],
                question_type=q["question_type"],
                difficulty=q["difficulty"],
                content=json.dumps(q["content"]),
                answer=json.dumps(q["answer"]),
                explanation=q.get("explanation", ""),
                source=q["source"]
            )
            session.add(db_q)
        await session.commit()
    
    logger.info("Done.")

if __name__ == "__main__":
    asyncio.run(main())
