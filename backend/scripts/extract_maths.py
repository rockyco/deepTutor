import asyncio
import base64
import json
import os
import sys
from playwright.async_api import async_playwright

# --- CONFIGURATION ---
URL = "https://www.cgpbooks.co.uk/CGPBooks/media/Applications/ElevenPlusOnline_FreeSample_20241220/"
SUBJECT_KEY = "maths" # Change this for other subjects
OUTPUT_DIR = f"backend/data/images/granular_{SUBJECT_KEY}"
METADATA_FILE = f"{OUTPUT_DIR}/metadata.json"
# ---------------------

os.makedirs(OUTPUT_DIR, exist_ok=True)

async def extract_images():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print(f"Navigating to {URL}...")
        await page.goto(URL)
        await page.wait_for_timeout(3000)
        
        # NOTE: Selector strategy needs to be adapted per test
        # Here we assume Maths is the 2nd button (Index 1) for example.
        # User must verify index or text.
        print(f"Looking for test button for {SUBJECT_KEY}...")
        
        # Heuristic finding based on text
        buttons = await page.get_by_text("Free sample test").all()
        target_btn = None
        
        # This logic tries to find the button associated with clear text headers
        # Use simple index fallback if needed:
        # Maths is often 2nd. NVR is 3rd. Verbal is 1st.
        if SUBJECT_KEY == "maths":
             # Try index 1
             if len(buttons) > 1:
                 target_btn = buttons[1]
             else:
                 print("Not enough buttons found.")
        elif SUBJECT_KEY == "non_verbal_reasoning":
             if len(buttons) > 2:
                 target_btn = buttons[2]

        if target_btn:
            await target_btn.click()
        else:
             print("Could not identify button automatically. Please click manually in headful mode (wait 10s).")
             await page.wait_for_timeout(10000)

        await page.wait_for_timeout(3000)
        
        all_metadata = []
        
        # Loop for 5-10 questions
        for q_num in range(1, 11): # Loop up to 10
            print(f"Processing Q{q_num}...")
            
            # Navigation (Clicking numbered squares)
            nav_squares = page.locator(".nav-square")
            if await nav_squares.count() > 0:
                 if q_num <= await nav_squares.count():
                     await nav_squares.nth(q_num - 1).click()
                     await page.wait_for_timeout(2000)
                 else:
                     break # No more questions
            else:
                 # Try Next button if no squares
                 pass

            # Screenshot
            await page.screenshot(path=f"{OUTPUT_DIR}/q{q_num}_screenshot.png")
            
            # Extract Text
            try:
                text = await page.evaluate("() => document.body.innerText.split('\\n')[0]") # Simple extraction
            except:
                text = "Could not extract text"

            # Extract Images
            img_data = await page.evaluate("""
                () => {
                    return Array.from(document.querySelectorAll('img'))
                        .filter(img => img.src.startsWith('data:image'))
                        .map(img => img.src)
                }
            """)
            
            q_data = {
                "question_num": q_num,
                "text": text,
                "images": []
            }
            
            for i, src in enumerate(img_data):
                b64 = src.split(',')[1]
                filename = f"q{q_num}_img_{i}.png"
                filepath = f"{OUTPUT_DIR}/{filename}"
                with open(filepath, "wb") as f:
                    f.write(base64.b64decode(b64))
                q_data["images"].append(filename)
                
            all_metadata.append(q_data)

        with open(METADATA_FILE, "w") as f:
            json.dump(all_metadata, f, indent=2)
            
        print(f"Saved metadata to {METADATA_FILE}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(extract_images())
