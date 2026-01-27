
import fitz
from pathlib import Path

def analyze_pdf(path):
    doc = fitz.open(path)
    print(f"Analyzing {path.name}...")
    
    for i in range(min(3, len(doc))): # First 3 pages
        page = doc[i]
        print(f"\n--- Page {i+1} ---")
        blocks = page.get_text("blocks")
        # Sort by vertical then horizontal
        blocks.sort(key=lambda b: (b[1], b[0])) 
        
        for b in blocks:
            x0, y0, x1, y1, text, block_no, block_type = b
            clean_text = text.strip().replace('\n', '\\n')
            if clean_text:
                print(f"[x={x0:.1f}, y={y0:.1f}] {clean_text[:100]}")

if __name__ == "__main__":
    base_dir = Path("/home/amd/UTS/deepTutor/samples")
    # Analyze one from each category
    files = list(base_dir.rglob("*.pdf"))
    for f in files[:2]: # Just take first 2 for now
        analyze_pdf(f)
