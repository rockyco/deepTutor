
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent / "data" / "images" / "granular"
METADATA_FILE = BASE_DIR / "nvr_metadata.json"
ANSWERS_FILE = BASE_DIR / "nvr_answers.json"

def merge():
    with open(METADATA_FILE) as f:
        metadata = json.load(f)
    
    with open(ANSWERS_FILE) as f:
        answers = json.load(f)
    
    for q in metadata:
        q_num = str(q["question_num"])
        if q_num in answers:
            q["answer"] = answers[q_num]
            print(f"Updated Q{q_num} answer to {answers[q_num]}")
        else:
            print(f"Warning: No answer for Q{q_num}")
            q["answer"] = "A" # Fallback

    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)
    print("Metadata updated.")

if __name__ == "__main__":
    merge()
