"""
Delete corrupted question data files to prepare for re-extraction.

This script removes the corrupted JSON files that contain:
- VR questions with garbled text (option letters mixed into content)
- English questions with placeholder text
"""

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / "backend" / "data" / "questions"

FILES_TO_DELETE = [
    "gl_vr_imported.json",
    "gl_english_imported.json",
    "cgp_english_imported.json",
    "all_extracted_questions.json",
]


def main():
    """Delete corrupted question files."""
    print("Deleting corrupted question files")
    print("=" * 50)

    deleted = []
    for filename in FILES_TO_DELETE:
        filepath = DATA_DIR / filename
        if filepath.exists():
            # Show sample of what we're deleting
            try:
                with open(filepath) as f:
                    data = json.load(f)
                print(f"\n{filename}: {len(data)} questions")
                if data and isinstance(data, list):
                    sample = data[0]
                    text = sample.get('content', {}).get('text', '')[:100]
                    print(f"  Sample: {text}...")
            except Exception as e:
                print(f"  Error reading: {e}")

            filepath.unlink()
            deleted.append(filename)
            print(f"  DELETED: {filepath}")
        else:
            print(f"\n{filename}: Not found (skipping)")

    print(f"\n\nDeleted {len(deleted)} files: {', '.join(deleted)}")
    print("Ready for re-extraction.")


if __name__ == "__main__":
    main()
