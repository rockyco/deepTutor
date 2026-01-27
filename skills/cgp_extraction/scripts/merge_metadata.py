import json
from pathlib import Path

# --- CONFIGURATION ---
SUBJECT_KEY = "non_verbal_reasoning"
BASE_DIR = Path(f"backend/data/images/granular_{SUBJECT_KEY}")
METADATA_FILE = BASE_DIR / "metadata.json"
ANSWERS_FILE = BASE_DIR / "answers.json"
# ---------------------

def merge():
    if not METADATA_FILE.exists() or not ANSWERS_FILE.exists():
        print("Metadata or Answers file not found.")
        print(f"Checked: {METADATA_FILE} and {ANSWERS_FILE}")
        return

    with open(METADATA_FILE) as f:
        metadata = json.load(f)
    
    with open(ANSWERS_FILE) as f:
        answers = json.load(f)
    
    updated_count = 0
    for q in metadata:
        q_num = str(q["question_num"])
        if q_num in answers:
            ans_data = answers[q_num]
            # Handle both simple string format and object format
            if isinstance(ans_data, dict):
                q["answer"] = ans_data.get("answer", "A")
                q["explanation"] = ans_data.get("explanation", "")
            else:
                q["answer"] = ans_data
                q["explanation"] = ""
            
            updated_count += 1
        else:
            print(f"Warning: No answer for Q{q_num}")
            q["answer"] = "A" # Fallback

    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata updated for {updated_count} questions.")

if __name__ == "__main__":
    merge()
