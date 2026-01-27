import asyncio
import base64
import json
import os
import sys
from playwright.async_api import async_playwright

# --- CONFIGURATION ---
# --- CONFIGURATION ---
URL = "https://www.cgpbooks.co.uk/11-plus-free-sample"
SUBJECT_KEY = "non_verbal_reasoning" 
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
        # Get actual Frame object
        iframe_element = await page.locator("iframe.display-app-container").element_handle()
        frame = await iframe_element.content_frame()
        
        print(f"Looking for test button for {SUBJECT_KEY} inside iframe...")
        try:
            # Robust selector for NVR
            if SUBJECT_KEY == "non_verbal_reasoning":
                start_btn = frame.locator(".dashboard-group").filter(has_text="GL Non-Verbal Reasoning").locator("button.free-sample-test")
            else:
                # Fallback or other subjects
                start_btn = frame.locator("button.free-sample-test").nth(1) 
            
            await start_btn.click()
            print("Clicked start button.")
        except Exception as e:
            print(f"Error clicking start button: {e}")
            await page.screenshot(path="debug_nvr_start_fail.png")
            return

        await page.wait_for_timeout(3000)
        
        all_metadata = []
        
        # Wait for first question to load
        await frame.locator("#question-content").first.wait_for(timeout=10000)

        all_metadata = []
        
        # Loop for 5-10 questions
        for q_num in range(1, 11): # Loop up to 10
            print(f"Processing Q{q_num}...")
            
            # Navigation (Clicking numbered squares)
            nav_squares = frame.locator(".nav-square")
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
                text = await frame.locator("#question-content").inner_text()
                text = text.split('\n')[0]
            except:
                text = "Could not extract text"

            # Extract Images
            # Segregate Question Image vs Option Images
            images_data = await frame.evaluate("""
                () => {
                    // Question Image: Usually inside #question-content
                    const qContainer = document.querySelector('#question-content');
                    const qImg = qContainer ? qContainer.querySelector('img') : null;
                    const qImgSrc = qImg && qImg.src.startsWith('data:image') ? qImg.src : null;

                    // Option Images: Associated with buttons or answer text
                    // We assume there are 5 options. They are often in .answer-container or similar, or just next images.
                    // A robust way for NVR is to look for images that are NOT the question image.
                    // Or specifically target the answer images if they have a class.
                    
                    const allImages = Array.from(document.querySelectorAll('img'));
                    const optionImages = allImages
                        .filter(img => img !== qImg && img.src.startsWith('data:image'))
                        .map(img => img.src);

                    return {
                        question_image: qImgSrc,
                        option_images: optionImages
                    };
                }
            """)
            
            q_data = {
                "question_num": q_num,
                "text": text,
                "question_image": None,
                "images": [] 
            }

            # Save Question Image
            if images_data['question_image']:
                b64 = images_data['question_image'].split(',')[1]
                filename = f"q{q_num}_question.png"
                filepath = f"{OUTPUT_DIR}/{filename}"
                with open(filepath, "wb") as f:
                    f.write(base64.b64decode(b64))
                q_data["question_image"] = filename

            # Save Option Images
            for i, src in enumerate(images_data['option_images']):
                b64 = src.split(',')[1]
                filename = f"q{q_num}_option_{i}.png"
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
