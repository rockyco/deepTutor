"""
Extract NVR questions from PASSNVR PDF as high-resolution PNG images.

Uses PyMuPDF at 600 DPI for clean rendering without PDF artifacts.
"""

import re
import json
import uuid
import sys
from pathlib import Path

# Direct import from vector_extractor module (avoid crawlers package __init__)
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR / "app" / "crawlers"))

from vector_extractor import VectorExtractor, save_png

# Configuration
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
PDF_PATH = PROJECT_ROOT / "samples" / "NVR" / "PASSNVR-FREE-Qs.pdf"
OUTPUT_DIR = PROJECT_ROOT / "backend" / "data" / "images" / "nvr" / "passnvr"
OUTPUT_JSON = PROJECT_ROOT / "backend" / "data" / "questions" / "passnvr_imported.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

# Hardcoded Section Mapping for PASSNVR-FREE-Qs.pdf
SECTION_RANGES = [
    (1, 5, "nvr_odd_one_out", "Classes Unlike", "Find the figure that is most unlike the others."),
    (6, 10, "nvr_rotation", "Rotation", "Find the figure that is a rotation of the first figure."),
    (11, 15, "nvr_codes", "Horizontal Codes", "Find the code that matches the shape."),
    (16, 20, "nvr_matrices", "Matrices", "Find the figure that completes the matrix."),
    (21, 25, "nvr_sequences", "Series", "Find the figure that continues the series."),
    (26, 30, "nvr_analogies", "Analogies", "Find the figure that completes the second pair."),
    (31, 35, "nvr_spatial_3d", "Nets", "Find the cube that can be made from the net."),
    (36, 40, "nvr_sequences", "Classes Like", "Find the figure that belongs to the same group as the first few."),
    (41, 45, "nvr_spatial_3d", "Block Counting", "How many blocks are in the figure?"),
    (46, 50, "nvr_spatial_3d", "Fold and Punch", "Find the pattern produced when the paper is unfolded.")
]


def get_section_info(q_num):
    for start, end, q_type, title, text in SECTION_RANGES:
        if start <= q_num <= end:
            return q_type, title, text
    return "non_verbal_reasoning", "Unknown", "Select the correct option."


def get_answer_key(extractor):
    print("Extracting answer key...")
    answers = {}
    if extractor.page_count <= 24:
        print("Error: PDF too short for answer key")
        return {}
    text = extractor.extract_text(24)
    matches = re.findall(r"(\d+)\.\s*([A-E])", text)
    for q_num, ans in matches:
        answers[int(q_num)] = ans
    return answers


def extract_questions(pdf_path):
    questions = []

    with VectorExtractor(pdf_path) as extractor:
        answers = get_answer_key(extractor)
        if not answers:
            return

        for page_idx in range(min(24, extractor.page_count)):
            page_width, page_height = extractor.get_page_dimensions(page_idx)
            words = extractor.extract_words(page_idx)

            q_nums = [w for w in words if w['text'].isdigit() and float(w['x0']) < 70]
            q_nums = [w for w in q_nums if float(w['top']) < 800]

            if not q_nums:
                continue

            q_nums.sort(key=lambda w: float(w['top']))

            for i, q_word in enumerate(q_nums):
                q_val = int(q_word['text'])
                if q_val not in answers:
                    continue

                row_top = float(q_word['top']) - 10

                if i < len(q_nums) - 1:
                    row_bottom = float(q_nums[i+1]['top']) - 10
                else:
                    row_bottom = page_height - 50

                if row_bottom - row_top < 40:
                    continue

                print(f"  Extracting Q{q_val} (Type: {get_section_info(q_val)[1]})")

                q_type, section_title, q_text = get_section_info(q_val)

                row_words = [w for w in words if row_top < float(w['top']) < row_bottom]
                label_a = next((w for w in row_words if w['text'] == 'A'), None)

                stimulus_img_path = None
                option_urls = []

                if label_a:
                    split_x = float(label_a['x0']) - 10

                    gap = split_x - float(q_word['x1'])
                    has_stimulus = gap > 100

                    if q_type == "nvr_odd_one_out":
                        has_stimulus = False
                    elif q_type == "nvr_analogies":
                        has_stimulus = True
                    elif q_type == "nvr_codes":
                        has_stimulus = True

                    opt_top = float(label_a['top']) - 10
                    if opt_top < row_top:
                        opt_top = row_top

                    if has_stimulus:
                        stim_box = (float(q_word['x1']) + 5, row_top, split_x, row_bottom)
                        try:
                            png_data = extractor.extract_region_as_png(page_idx, stim_box)
                            stim_filename = f"q{q_val}_stimulus.png"
                            stim_path = OUTPUT_DIR / stim_filename
                            save_png(png_data, stim_path)
                            stimulus_img_path = f"/images/nvr/passnvr/{stim_filename}"
                        except Exception as e:
                            print(f"Error extracting stimulus Q{q_val}: {e}")

                    labels = [w for w in row_words if w['text'] in ['A', 'B', 'C', 'D', 'E']]
                    labels.sort(key=lambda w: float(w['x0']))

                    if len(labels) == 5:
                        for j, lbl in enumerate(labels):
                            if j == 0:
                                start_x = split_x
                            else:
                                start_x = (float(labels[j-1]['x1']) + float(lbl['x0'])) / 2

                            if j == 4:
                                end_x = page_width - 40
                            else:
                                end_x = (float(lbl['x1']) + float(labels[j+1]['x0'])) / 2

                            sub_box = (start_x, opt_top, end_x, row_bottom)
                            try:
                                png_data = extractor.extract_region_as_png(page_idx, sub_box)
                                sub_filename = f"q{q_val}_opt_{lbl['text']}.png"
                                sub_path = OUTPUT_DIR / sub_filename
                                save_png(png_data, sub_path)
                                option_urls.append(f"/images/nvr/passnvr/{sub_filename}")
                            except Exception as e:
                                print(f"Error extracting option {lbl['text']} Q{q_val}: {e}")

                if len(option_urls) != 5 and not option_urls:
                    continue

                q_obj = {
                    "id": str(uuid.uuid4()),
                    "subject": "non_verbal_reasoning",
                    "question_type": q_type,
                    "format": "multiple_choice",
                    "difficulty": 3,
                    "content": {
                        "text": q_text,
                        "image_url": stimulus_img_path,
                        "options": option_urls
                    },
                    "answer": {
                        "value": "",
                        "case_sensitive": False
                    },
                    "explanation": f"Section: {section_title}. See answer key.",
                    "tags": ["passnvr", "gl-assessment", section_title],
                    "source": "PASSNVR-FREE-Qs.pdf"
                }

                if option_urls and len(option_urls) == 5:
                    ans_char = answers[q_val]
                    ans_idx = ord(ans_char) - ord('A')
                    if 0 <= ans_idx < 5:
                        q_obj["answer"]["value"] = option_urls[ans_idx]

                questions.append(q_obj)

    with open(OUTPUT_JSON, 'w') as f:
        json.dump(questions, f, indent=2)
    print(f"Saved {len(questions)} questions to {OUTPUT_JSON}")


if __name__ == "__main__":
    extract_questions(PDF_PATH)
