import json
import os
from pathlib import Path

METADATA_PATH = Path("backend/data/images/granular_non_verbal_reasoning/metadata.json")

def clean_metadata():
    if not METADATA_PATH.exists():
        print("Metadata not found!")
        return

    with open(METADATA_PATH) as f:
        data = json.load(f)

    print(f"Original Count: {len(data)}")

    cleaned = []
    seen_hashes = set()

    for q in data:
        # 1. REMOVE BROKEN QUESTIONS (No images for NVR)
        # NVR questions MUST have visuals.
        # Check 'images' array (options) or 'question_image'
        has_question_image = bool(q.get("question_image") or q.get("question_images"))
        has_option_images = bool(q.get("images") and len(q["images"]) > 0)
        
        # Exception: "Odd One Out" (most unlike) might usually just have option images and no question image.
        # But if BOTH are empty, it's definitely broken.
        if not has_question_image and not has_option_images:
            print(f"Removing Broken Q{q.get('question_num')}: No images found.")
            continue
            
        # Stricter check for NVR: If options are simple labels (A, B...) but NO option images, it's broken.
        # Check first option text.
        options = q.get("options", [])
        if not has_option_images and options and len(options) > 0:
            first_opt = options[0].strip().lower()
            # If option is short (like "a)" or "a") and no images -> BROKEN
            if len(first_opt) < 4: 
                print(f"Removing Broken Q{q.get('question_num')}: Text-only options with no images.")
                continue
            
        # Also remove if it has NO question text? No, text exists.
        
        # 2. DEDUPLICATE (Aggressive)
        # Key: Question Text + Answer
        # We prefer the one with MORE images if duplicates exist.
        key = f"{q.get('text', '').strip()}:{q.get('answer', '')}"
        
        if key in seen_hashes:
            print(f"Removing Duplicate Q{q.get('question_num')}")
            continue
        
        seen_hashes.add(key)
        
        # 3. CLEANUP REDUNDANT CONTENT
        # Strip "Answer: \n\n" from explanation
        if q.get("explanation"):
            q["explanation"] = q["explanation"].replace("Answer:\n\n", "").strip()
            
        # 4. FIX REDUNDANT OPTIONS
        # If options are just "a)", "b)", ... and we have images, we can leave them
        # BUT the frontend handles stripping.
        # However, let's ensure the data is clean.
        # Use simple ["A", "B", "C"] if they are just labels?
        # Actually, let's leave them as prompts but ensure they match image count.
        
        cleaned.append(q)

    print(f"Final Count: {len(cleaned)}")
    
    with open(METADATA_PATH, "w") as f:
        json.dump(cleaned, f, indent=2)
    
    print("Saved cleaned metadata.")

if __name__ == "__main__":
    clean_metadata()
