#!/usr/bin/env python3
"""
Fix GL Assessment NVR option image cropping.

The original extraction script cropped option images from PDF page coordinates,
producing blank or incorrectly cropped images. This script:
1. Scans for gl_nvr*_q*.png files in the NVR images directory
2. Detects the layout (divider, odd-one-out, or analogy)
3. Re-crops 5 option images from each full question PNG
4. Creates question-only images (left portion without options)
5. Updates metadata.json with GL NVR entries (adds or updates them)

Usage:
    cd backend && uv run python scripts/fix_nvr_options.py
"""

import json
import os
import re
from pathlib import Path

import numpy as np
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent.parent
IMG_DIR = BASE_DIR / "data" / "images" / "granular_non_verbal_reasoning"
METADATA_PATH = IMG_DIR / "metadata.json"


def find_content_blocks(img: Image.Image) -> list[tuple[int, int]]:
    """Find horizontal content blocks in the image.

    Scans columns in the vertical middle band (20%-80%) for non-white content.
    Returns list of (x_start, x_end) for each contiguous block >= 10px wide.
    """
    arr = np.array(img.convert("L"))
    h, w = arr.shape

    shape_band = arr[int(h * 0.20):int(h * 0.80), :]
    col_content = (shape_band < 220).sum(axis=0)

    threshold = 3
    in_content = False
    blocks = []
    start = 0
    for x in range(w):
        has = col_content[x] > threshold
        if has and not in_content:
            start = x
            in_content = True
        elif not has and in_content:
            blocks.append((start, x))
            in_content = False
    if in_content:
        blocks.append((start, w))

    return [(s, e) for s, e in blocks if e - s >= 10]


def find_vertical_divider(img: Image.Image) -> int | None:
    """Find x-position of a narrow dark vertical divider line.

    Scans 30-55% of width for a dark column covering >20% of the vertical band.
    Validates that it's narrow (neighbors are lighter) and not inside a content block.
    """
    arr = np.array(img.convert("L"))
    h, w = arr.shape

    search_start = int(w * 0.30)
    search_end = int(w * 0.55)

    top = int(h * 0.15)
    bot = int(h * 0.75)
    mid_band = arr[top:bot, :]
    band_height = bot - top

    dark_counts = (mid_band < 128).sum(axis=0)

    search_slice = dark_counts[search_start:search_end]
    if len(search_slice) == 0:
        return None

    max_dark = int(search_slice.max())
    divider_x = search_start + int(np.argmax(search_slice))

    if max_dark / band_height < 0.20:
        return None

    # Divider must be narrow: neighbors significantly lighter
    left_region = dark_counts[max(divider_x - 10, 0):max(divider_x - 2, 0)]
    right_region = dark_counts[min(divider_x + 2, w):min(divider_x + 10, w)]
    left_avg = left_region.mean() if len(left_region) > 0 else 0
    right_avg = right_region.mean() if len(right_region) > 0 else 0

    if left_avg > max_dark * 0.6 and right_avg > max_dark * 0.6:
        return None

    return divider_x


def detect_options(img: Image.Image) -> tuple[list[tuple[int, int]], int | None, bool]:
    """Detect 5 option blocks and classify the layout.

    Returns:
        option_blocks: list of 5 (x_start, x_end) tuples
        divider_x: divider position (or effective divider), or None
        is_full_width: True for odd-one-out (options span full width)
    """
    w, h = img.size
    blocks = find_content_blocks(img)
    significant = [(s, e) for s, e in blocks if e - s >= 40]

    divider_x = find_vertical_divider(img)

    # Reject divider if it falls inside a content block (not a real gap)
    if divider_x is not None:
        for s, e in blocks:
            if s <= divider_x <= e:
                divider_x = None
                break

    # Check for odd-one-out: 5 evenly-spaced blocks spanning most of the width
    if len(significant) == 5:
        centers = [(s + e) / 2 for s, e in significant]
        spacings = [centers[i + 1] - centers[i] for i in range(4)]
        avg_sp = sum(spacings) / 4
        span = significant[-1][1] - significant[0][0]
        if (significant[0][0] < w * 0.25
                and span > w * 0.60
                and avg_sp > 0
                and all(abs(s - avg_sp) < avg_sp * 0.3 for s in spacings)):
            return significant, None, True

    if divider_x is not None:
        # Divider layout: options are content blocks to the right
        right_blocks = [(s, e) for s, e in significant if s > divider_x]
        if len(right_blocks) >= 5:
            return right_blocks[:5], divider_x, False
        if len(right_blocks) > 0:
            return _extrapolate_options(right_blocks, w), divider_x, False
        return _uniform_right(divider_x, w), divider_x, False

    # No divider: check for analogy layout (>5 blocks, last 5 evenly spaced)
    if len(significant) >= 6:
        candidate = significant[-5:]
        centers = [(s + e) / 2 for s, e in candidate]
        spacings = [centers[i + 1] - centers[i] for i in range(4)]
        avg_sp = sum(spacings) / 4
        if avg_sp > 0 and all(abs(s - avg_sp) < avg_sp * 0.35 for s in spacings):
            stim_end = significant[-6][1]
            eff_divider = (stim_end + candidate[0][0]) // 2
            return candidate, eff_divider, False

    # Fallback: split at 40%
    split = int(w * 0.40)
    return _uniform_right(split, w), split, False


def _extrapolate_options(detected_blocks, img_width):
    """Extrapolate 5 option positions from fewer detected blocks."""
    if len(detected_blocks) >= 2:
        stride = detected_blocks[1][0] - detected_blocks[0][0]
        bw = detected_blocks[0][1] - detected_blocks[0][0]
    else:
        bw = detected_blocks[0][1] - detected_blocks[0][0]
        stride = int((img_width * 0.90 - detected_blocks[0][0]) / 5)

    s0 = detected_blocks[0][0]
    result = []
    for i in range(5):
        start = s0 + i * stride
        end = min(start + bw, img_width)
        if start >= end:
            start = max(end - bw, 0)
        result.append((start, end))
    return result


def _uniform_right(divider_x, img_width):
    """Create 5 uniform option blocks after the divider."""
    opt_start = divider_x + 30
    opt_end = int(img_width * 0.90)
    opt_w = (opt_end - opt_start) / 5
    return [(int(opt_start + i * opt_w), int(opt_start + (i + 1) * opt_w)) for i in range(5)]


def crop_images(img: Image.Image, option_blocks: list[tuple[int, int]], divider_x: int | None, is_full_width: bool) -> tuple[Image.Image | None, list[Image.Image]]:
    """Crop question-only image and 5 option images."""
    w, h = img.size

    opt_top = int(h * 0.08)
    opt_bottom = int(h * 0.92)
    padding = 10

    crops = []
    for s, e in option_blocks:
        x1 = max(s - padding, 0)
        x2 = min(e + padding, w)
        crops.append(img.crop((x1, opt_top, x2, opt_bottom)))

    q_img = None
    if not is_full_width and divider_x is not None:
        q_right = min(divider_x - 3, option_blocks[0][0] - 5)
        if q_right > 50:
            q_img = img.crop((0, 0, q_right, h))

    return q_img, crops


def scan_gl_nvr_images() -> dict[str, list[str]]:
    """Scan for GL NVR question images, grouped by booklet.

    Returns dict like: {"gl_nvr1": ["gl_nvr1_q1.png", "gl_nvr1_q2.png", ...]}
    Only includes main question images (not _opt* or _qonly files).
    """
    pattern = re.compile(r"^(gl_nvr\d+)_q(\d+)\.png$")
    booklets: dict[str, list[str]] = {}

    for fname in sorted(os.listdir(IMG_DIR)):
        m = pattern.match(fname)
        if m:
            booklet = m.group(1)
            booklets.setdefault(booklet, []).append(fname)

    return booklets


def is_nvr_question(img: Image.Image) -> bool:
    """Check if image is an NVR question (not maths/data from mixed papers).

    NVR questions are 455-570px tall with blue A-E labels in bottom portion.
    """
    w, h = img.size
    if h > 650:
        return False

    arr = np.array(img.convert("RGB"))
    bottom = arr[int(h * 0.70):, :, :]
    br, bg, bb = bottom[:, :, 0].astype(int), bottom[:, :, 1].astype(int), bottom[:, :, 2].astype(int)
    blue_mask = (bb > 100) & (bb > br + 10) & (bb > bg)
    return blue_mask.sum() > 30


def main():
    os.chdir(IMG_DIR)

    # Load existing metadata
    with open(METADATA_PATH) as f:
        metadata = json.load(f)

    # Remove any existing GL NVR entries (we'll re-add them)
    metadata = [e for e in metadata if not str(e.get("question_image", "")).startswith("gl_nvr")]

    booklets = scan_gl_nvr_images()
    fixed = 0
    skipped = 0

    for booklet, files in sorted(booklets.items()):
        booklet_num = booklet.replace("gl_nvr", "")
        source = f"GL Assessment NVR {booklet_num}"
        print(f"\n{source} ({len(files)} images)")

        for fname in files:
            img = Image.open(fname)
            qnum_match = re.search(r"_q(\d+)\.", fname)
            qnum = int(qnum_match.group(1)) if qnum_match else 0

            # Skip non-NVR images from mixed papers (booklet 11)
            if booklet_num == "11" and not is_nvr_question(img):
                skipped += 1
                continue

            # Detect layout and crop
            option_blocks, divider_x, is_full_width = detect_options(img)
            q_img, opt_crops = crop_images(img, option_blocks, divider_x, is_full_width)

            if is_full_width:
                layout = "odd_one_out"
            elif divider_x is not None:
                layout = "divider"
            else:
                layout = "fallback"

            # Save option images
            opt_names = []
            for i, crop in enumerate(opt_crops):
                opt_name = f"{booklet}_q{qnum}_opt{i}.png"
                crop.save(opt_name)
                opt_names.append(opt_name)

            # Save question-only image
            qonly_name = None
            if q_img is not None:
                qonly_name = f"{booklet}_q{qnum}_qonly.png"
                q_img.save(qonly_name)

            # Create metadata entry
            entry = {
                "question_num": qnum,
                "text": "Look at the shapes. Choose the correct answer.",
                "question_image": qonly_name if qonly_name else fname,
                "question_images": [qonly_name] if qonly_name else [fname],
                "images": opt_names,
                "answer": "Unknown",  # Will be set from answer key
                "explanation": "",
                "options": ["a)", "b)", "c)", "d)", "e)"],
                "source": source,
                "nvr_type": "nvr_visual",
            }
            metadata.append(entry)

            fixed += 1
            print(f"  [{layout:>13}] {fname} -> 5 opts" + (" + qonly" if qonly_name else ""))

    # Save updated metadata
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\nDone.")
    print(f"  Fixed: {fixed}")
    print(f"  Skipped (non-NVR): {skipped}")
    print(f"  Total metadata entries: {len(metadata)}")


if __name__ == "__main__":
    main()
