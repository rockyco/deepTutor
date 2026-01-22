"""
Extract NVR questions from GL Assessment PDFs as high-resolution PNG images.

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
SAMPLES_DIR = PROJECT_ROOT / "samples" / "NVR" / "GL1-3"
GUIDE_PATH = SAMPLES_DIR / "Non-Verbal Reasoning_Parent's Guide.pdf"
OUTPUT_DIR_BASE = PROJECT_ROOT / "backend" / "data" / "images" / "nvr"
OUTPUT_JSON = PROJECT_ROOT / "backend" / "data" / "questions" / "gl_imported.json"

OUTPUT_DIR_BASE.mkdir(parents=True, exist_ok=True)
OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

# Section Mappings (StartQ, EndQ, Type, Title)
BOOKLET_SECTIONS = {
    1: [
        (1, 20, "nvr_sequences", "Series"),
        (21, 40, "nvr_analogies", "Analogies"),
        (41, 60, "nvr_odd_one_out", "Classes Like"),
        (61, 80, "nvr_codes", "Codes"),
    ],
    2: [
        (1, 20, "nvr_odd_one_out", "Classes Like"),
        (21, 40, "nvr_sequences", "Series"),
        (41, 60, "nvr_odd_one_out", "Odd One Out"),
        (61, 80, "nvr_codes", "Codes"),
    ],
    3: [
        (1, 20, "nvr_analogies", "Analogies"),
        (21, 40, "nvr_matrices", "Matrices"),
        (41, 60, "nvr_codes", "Codes"),
        (61, 80, "nvr_odd_one_out", "Classes Like"),
    ]
}

# Answer Page Index in Parent's Guide (0-based)
ANSWER_PAGES = {
    1: 5,  # Page 6
    2: 6,  # Page 7
    3: 7   # Page 8
}


def get_answer_key(guide_path, booklet_num):
    """Extract answers for specific booklet from Parent's Guide page."""
    print(f"Extracting answers for Booklet {booklet_num}...")
    answers = {}
    page_idx = ANSWER_PAGES.get(booklet_num)

    with VectorExtractor(guide_path) as extractor:
        if page_idx is None or page_idx >= extractor.page_count:
            print(f"Error: Guide page {page_idx} out of range")
            return {}

        text = extractor.extract_text(page_idx)

    matches = re.findall(r"(\d+)\.\s*([A-E])", text)

    for q_num, ans in matches:
        q_num = int(q_num)
        if 1 <= q_num <= 80:
            answers[q_num] = ans

    print(f"Found {len(answers)} answers for Booklet {booklet_num}")
    return answers


def get_section_info(q_num, booklet_num):
    sections = BOOKLET_SECTIONS.get(booklet_num, [])
    for start, end, q_type, title in sections:
        if start <= q_num <= end:
            return q_type, title
    return "non_verbal_reasoning", "Unknown"


def extract_booklet(booklet_num, guide_path):
    if booklet_num == 1:
        pdf_path = SAMPLES_DIR / f"Non-Verbal Reasoning_{booklet_num}_ Test Booklet.pdf"
    else:
        pdf_path = SAMPLES_DIR / f"Non-Verbal Reasoning_{booklet_num}_Test Booklet.pdf"

    img_dir = OUTPUT_DIR_BASE / f"gl{booklet_num}"
    img_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing {pdf_path}...")

    questions = []
    answers = get_answer_key(guide_path, booklet_num)
    if not answers:
        return []

    with VectorExtractor(pdf_path) as extractor:
        page_width, page_height = extractor.get_page_dimensions(0)

        for page_idx in range(extractor.page_count):
            page_width, page_height = extractor.get_page_dimensions(page_idx)
            words = extractor.extract_words(page_idx)

            q_nums = [w for w in words if w['text'].isdigit() and float(w['x0']) < 70]
            q_nums = [w for w in q_nums if float(w['bottom']) < page_height - 50]

            if not q_nums:
                continue

            q_nums.sort(key=lambda w: float(w['top']))

            valid_qs = []
            seen_qs = set()
            for w in q_nums:
                val = int(w['text'])
                if val in answers and val not in seen_qs:
                    valid_qs.append(w)
                    seen_qs.add(val)

            if not valid_qs:
                continue

            print(f"  Page {page_idx + 1}: Found Qs {[w['text'] for w in valid_qs]}")

            for i, q_word in enumerate(valid_qs):
                q_val = int(q_word['text'])

                row_top = float(q_word['top']) - 10
                if i < len(valid_qs) - 1:
                    row_bottom = float(valid_qs[i+1]['top']) - 10
                else:
                    row_bottom = page_height - 50

                if row_bottom - row_top < 40:
                    continue

                q_type, section_title = get_section_info(q_val, booklet_num)

                row_words = [w for w in words if row_top < float(w['top']) < row_bottom]

                # Loose check for 'A' label to tolerate slightly left positions
                label_a = next((w for w in row_words if w['text'] == 'A' and float(w['x0']) > 150), None)

                stimulus_img_path = None
                option_urls = []

                if label_a:
                    split_x = float(label_a['x0']) - 20

                    stim_left = float(q_word['x1']) + 10
                    has_stimulus = split_x - stim_left > 50

                    opt_top = float(label_a['top']) - 10
                    if opt_top < row_top:
                        opt_top = row_top

                    if q_type == "nvr_odd_one_out" and "Unlike" in section_title:
                        has_stimulus = False

                    if has_stimulus and split_x > stim_left:
                        stim_box = (stim_left, row_top, split_x, row_bottom)
                        try:
                            png_data = extractor.extract_region_as_png(page_idx, stim_box)
                            stim_filename = f"q{q_val}_stimulus.png"
                            stim_path = img_dir / stim_filename
                            save_png(png_data, stim_path)
                            stimulus_img_path = f"/images/nvr/gl{booklet_num}/{stim_filename}"
                        except Exception as e:
                            print(f"Error extracting stimulus for Q{q_val}: {e}")

                    labels = [w for w in row_words if w['text'] in ['A', 'B', 'C', 'D', 'E'] and float(w['x0']) > 150]
                    labels.sort(key=lambda w: float(w['x0']))

                    unique_labels = []
                    seen = set()
                    for lbl in labels:
                        if lbl['text'] not in seen:
                            unique_labels.append(lbl)
                            seen.add(lbl['text'])
                    labels = unique_labels

                    if len(labels) == 5:
                        for j, lbl in enumerate(labels):
                            if j == 0:
                                start_x = split_x
                            else:
                                start_x = (float(labels[j-1]['x1']) + float(lbl['x0'])) / 2

                            if j == 4:
                                end_x = page_width - 20
                            else:
                                end_x = (float(lbl['x1']) + float(labels[j+1]['x0'])) / 2

                            if start_x >= end_x - 5:
                                start_x = float(lbl['x0']) - 5
                                end_x = float(lbl['x1']) + 5

                            sub_box = (start_x, opt_top, end_x, row_bottom)
                            try:
                                png_data = extractor.extract_region_as_png(page_idx, sub_box)
                                sub_filename = f"q{q_val}_opt_{lbl['text']}.png"
                                sub_path = img_dir / sub_filename
                                save_png(png_data, sub_path)
                                option_urls.append(f"/images/nvr/gl{booklet_num}/{sub_filename}")
                            except Exception as e:
                                print(f"  Error extracting option {lbl['text']} for Q{q_val}: {e}")

                if not option_urls:
                    continue

                q_obj = {
                    "id": str(uuid.uuid4()),
                    "subject": "non_verbal_reasoning",
                    "question_type": q_type,
                    "format": "multiple_choice",
                    "difficulty": 3,
                    "content": {
                        "text": f"Select the correct option for question {q_val}.",
                        "image_url": stimulus_img_path,
                        "options": option_urls
                    },
                    "answer": {
                        "value": "",
                        "case_sensitive": False
                    },
                    "explanation": f"Section: {section_title}. See answer key.",
                    "tags": ["gl-assessment", f"gl-test-{booklet_num}", section_title],
                    "source": f"GL_Test_{booklet_num}.pdf"
                }

                ans_char = answers[q_val]
                ans_idx = ord(ans_char) - ord('A')
                if 0 <= ans_idx < 5:
                    q_obj["answer"]["value"] = option_urls[ans_idx]

                questions.append(q_obj)

    return questions


if __name__ == "__main__":
    all_questions = []
    for b_num in [1, 2, 3]:
        qs = extract_booklet(b_num, GUIDE_PATH)
        all_questions.extend(qs)

    with open(OUTPUT_JSON, 'w') as f:
        json.dump(all_questions, f, indent=2)

    print(f"Saved total {len(all_questions)} questions to {OUTPUT_JSON}")
