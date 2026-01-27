
import json
from pathlib import Path

# --- CONFIGURATION ---
SUBJECT_KEY = "maths"
BASE_DIR = Path(f"backend/data/cgp/{SUBJECT_KEY}")
RAW_FILE = BASE_DIR / "raw_crawl.json"
OUTPUT_DIR = Path(f"backend/data/images/granular_{SUBJECT_KEY}")
METADATA_FILE = OUTPUT_DIR / "metadata.json"

def process():
    file_to_read = RAW_FILE
    if not RAW_FILE.exists():
        partial_file = BASE_DIR / "partial_crawl.json"
        if partial_file.exists():
             print(f"Raw file not found, using partial file: {partial_file}")
             file_to_read = partial_file
        else:
             print(f"Raw file not found: {RAW_FILE}")
             return

    with open(file_to_read) as f:
        raw_data = json.load(f)

    processed_data = []
    
    for q in raw_data:
        # Convert Q ID
        # raw has 'id' (int). metadata usually expects 'question_num'
        
        # Ensure images are mapped
        # raw has 'images' list of paths relative to BASE_DIR/images
        # Metadata expects paths the frontend/backend can serve.
        # Actually update_db.py just stores the path.
        # We need to copy images to granularity folder?
        # crawl_maths_fixed saves to backend/data/cgp/maths/images
        
        # We should keep the data where it is or move it?
        # The app serves from backend/data.
        # update_db.py uses BASE_DIR = Path(f"backend/data/images/granular_{SUBJECT_KEY}")
        # So we should probably move images there or point update_db to new location.
        # Let's point update_db to the extracted data, OR copy data to granular_{subject}.
        
        # Simpler: Copy data to granular_{subject} structure.
        
        clean_q = {
            "question_num": q["id"],
            "text": q.get("text", "").strip(),
            "answer": q.get("correct_answer", "A"),
            "explanation": q.get("explanation", ""),
            "options": q.get("options", []),
            "images": q.get("images", []) # These are filenames in cgp/maths/images
        }
        
        # Copy images to output dir
        for img_name in clean_q["images"]:
            src_path = BASE_DIR / "images" / img_name
            dest_path = OUTPUT_DIR / img_name
            if src_path.exists():
                import shutil
                shutil.copy2(src_path, dest_path)
        
        processed_data.append(clean_q)

    # Ensure output dir exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(METADATA_FILE, "w") as f:
        json.dump(processed_data, f, indent=2)
        
    print(f"Processed {len(processed_data)} questions. Saved to {METADATA_FILE}")
    print(f"Copied images to {OUTPUT_DIR}")

if __name__ == "__main__":
    process()
