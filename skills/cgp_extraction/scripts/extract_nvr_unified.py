import asyncio
import base64
import json
import os
import re
import sys
from playwright.async_api import async_playwright

# --- CONFIGURATION ---
URL = "https://www.cgpbooks.co.uk/11-plus-free-sample"
SUBJECT_KEY = "non_verbal_reasoning"
OUTPUT_DIR = f"backend/data/images/granular_{SUBJECT_KEY}"
METADATA_FILE = f"{OUTPUT_DIR}/metadata.json"
# ---------------------

os.makedirs(OUTPUT_DIR, exist_ok=True)

async def extract_unified():
    async with async_playwright() as p:
        # Use headless=False for stability with sensitive CGP site
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print(f"Navigating to {URL}...")
        await page.goto(URL)
        await page.wait_for_timeout(3000)

        # --- PREPARATION ---
        # Dismiss cookies aggressively
        try:
             if await page.get_by_text("Accept all").count() > 0:
                 await page.get_by_text("Accept all").click(timeout=3000)
             elif await page.locator(".cookie-message-content").count() > 0:
                 await page.locator(".cookie-message-content").get_by_text("Accept").click(timeout=3000)
        except:
             pass

        # Locate iframe
        print("Locating iframe...")
        iframe_element = await page.locator("iframe.display-app-container").element_handle()
        frame = await iframe_element.content_frame()

        # Start Test
        print(f"Starting test for {SUBJECT_KEY}...")
        try:
             # Ensure wait
             await frame.locator(".dashboard-group").first.wait_for(timeout=10000)
             await frame.locator(".dashboard-group").filter(has_text="GL Non-Verbal Reasoning").locator("button.free-sample-test").click()
        except Exception as e:
             print(f"Failed to start test: {e}")
             await browser.close()
             return

        await frame.locator("#question-content").first.wait_for(timeout=20000)
        
        # --- PHASE 1: EXTRACT IMAGES & SUBMIT ANSWERS ---
        print("--- PHASE 1: Image Extraction & Submission ---")
        
        questions_map = {} # Key: q_num, Value: dict
        
        for q_num in range(1, 11):
            print(f"Processing Q{q_num} (Images & Answer Selection)...")
            
            # 1. Navigation (Ensure we are on correct question)
            # If not first question, click nav square
            if q_num > 1:
                try:
                    await frame.locator(f".nav-square >> text={q_num}").click()
                    await page.wait_for_timeout(1000)
                except:
                    pass
            
            # 2. Extract Text
            try:
                text = await frame.locator("#question-content").inner_text()
                text = text.split('\n')[0]
            except:
                text = "Could not extract text"

            # 3. Extract Images (Separated)
            images_data = await frame.evaluate("""
                () => {
                    const qContainer = document.querySelector('#question-content');
                    const qImg = qContainer ? qContainer.querySelector('img') : null;
                    const qImgSrc = qImg && qImg.src.startsWith('data:image') ? qImg.src : null;

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
                "images": [],
                "answer": "Unknown", # To be filled in Phase 2
                "explanation": ""    # To be filled in Phase 2
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
            
            questions_map[q_num] = q_data
            
            # 4. Select an Answer (Option A) to handle "Mark Test" requirements
            try:
                await frame.locator(".input-button").first.click(timeout=1000)
                await page.wait_for_timeout(200)
            except:
                pass
                
        # --- SUBMISSION ---
        print("Submitting test...")
        if await frame.get_by_text("Mark Test").count() > 0:
             await frame.get_by_text("Mark Test").click()
             await page.wait_for_timeout(2000)
             
             # Confirm modal loop (Robust)
             for i in range(5):
                 print(f"Confirm loop {i+1}...")
                 # Try JS click on visible element
                 clicked = await frame.evaluate("""
                    () => {
                        const btns = Array.from(document.querySelectorAll('.dialog-confirm-btn'));
                        const target = btns.find(b => b.innerText.includes('Mark Test') && b.offsetParent !== null);
                        if (target) {
                            target.click();
                            return true;
                        }
                        return false;
                    }
                 """)
                 
                 # Try fallback to page JS
                 if not clicked:
                     print("Checking page context...")
                     clicked = await page.evaluate("""
                        () => {
                            const btns = Array.from(document.querySelectorAll('.dialog-confirm-btn'));
                            const target = btns.find(b => b.innerText.includes('Mark Test') && b.offsetParent !== null);
                            if (target) {
                                target.click();
                                return true;
                            }
                            return false;
                        }
                     """)

                 if clicked:
                     print("Clicked visible confirm button via JS.")
                     await page.wait_for_timeout(3000)
                 
                 if await frame.locator("button").filter(has_text="Review my answers").count() > 0:
                     print("Review button appeared!")
                     break
                 
                 await page.wait_for_timeout(1000)

        # --- REVIEW PHASE ---
        print("Entering Review Mode...")
        try:
            await frame.locator("button").filter(has_text="Review my answers").wait_for(timeout=20000)
            await frame.locator("button").filter(has_text="Review my answers").click()
        except Exception as e:
            print(f"Review button not found: {e}")
            await page.screenshot(path="debug_unified_review_fail.png")
            await browser.close()
            return
            
        # --- PHASE 2: EXTRACT ANSWERS ---
        print("--- PHASE 2: Answer Extraction ---")
        
        for q_num in range(1, 11):
            print(f"Extracting Answer Q{q_num}...")
            # Navigate
            try:
                await frame.locator(f".nav-square >> text={q_num}").click()
                await page.wait_for_timeout(1000)
            except:
                pass

            # Extract Explanation & Answer Letter
            try:
                explanation_el = frame.locator(".answer-state").locator("..")
                full_text = await explanation_el.inner_text()
                
                match = re.search(r"The (?:correct )?answer is ([a-e])", full_text, re.IGNORECASE)
                answer_char = match.group(1).upper() if match else "Unknown"
                
                questions_map[q_num]["answer"] = answer_char
                questions_map[q_num]["explanation"] = full_text.strip()
                print(f"Q{q_num}: {answer_char}")
            except Exception as e:
                print(f"Error extraction Q{q_num}: {e}")

        # --- SAVE ---
        all_metadata = list(questions_map.values())
        with open(METADATA_FILE, "w") as f:
            json.dump(all_metadata, f, indent=2)
            
        print(f"Saved complete metadata to {METADATA_FILE}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(extract_unified())
