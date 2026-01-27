
import asyncio
import json
import base64
import os
import re
from pathlib import Path
from playwright.async_api import async_playwright

# --- CONFIGURATION ---
URL = "https://www.cgpbooks.co.uk/11-plus-free-sample"
SUBJECT_KEY = "maths"
BASE_DIR = Path(f"backend/data/cgp/{SUBJECT_KEY}")
IMAGES_DIR = BASE_DIR / "images"
RAW_OUTPUT = BASE_DIR / "raw_crawl.json"

os.makedirs(IMAGES_DIR, exist_ok=True)

async def crawl():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print(f"Navigating to {URL}...")
        await page.goto(URL)
        
        # 1. Access the Iframe
        print("Waiting for application iframe...")
        frame = None
        for attempt in range(20):
            for f in page.frames:
                if "ElevenPlusOnline" in f.url:
                    frame = f
                    break
            if frame:
                print(f"Found frame: {frame.url}")
                break
            await asyncio.sleep(1)
            
        if not frame:
            print("Iframe not found after searching page.frames.")
            # Debug: print all frame urls
            for f in page.frames:
                print(f"Frame: {f.url}")
            await browser.close()
            return

        # 2. Select Maths Test INSIDE the iframe
        print("Selecting Maths Test...")
        try:
             # Look for GL Maths card.
             # Subagent said: .dashboard-group:nth-of-type(1) .free-sample-test
             # Or search for text "GL Maths" inside the frame
             
             # Wait for dashboard to load
             await frame.wait_for_selector(".dashboard-group", timeout=10000)
             
             # Find the button
             # We can use the precise selector found by subagent
             await frame.locator(".dashboard-group").first.locator(".free-sample-test").click()
             
             # Alternative: verify it matches GL Maths
             # await frame.get_by_text("GL Maths").locator("..").locator(".free-sample-test").click()
        except Exception as e:
             print(f"Failed to click test button: {e}")
             await browser.close()
             return

        # Wait for the Question 1 to appear
        print("Waiting for Question 1...")
        try:
             # Wait for "Question 1" text to appear in the body
             # or .question class
             await frame.wait_for_selector(".question", timeout=15000)
        except:
             print("Question 1 did not load.")
             await browser.close()
             return

        questions_data = []

        # 3. Phase 1: Answer All Questions
        print("Starting Phase 1: Answering...")
        for i in range(1, 11):
            valid_q = False
            # Wait for "Question X" text
            for attempt in range(10):
                text = await frame.inner_text("body")
                if f"Question {i}" in text:
                    valid_q = True
                    break
                await asyncio.sleep(0.5)
            
            if not valid_q:
                print(f"Question {i} did not appear.")
                break

            print(f"Processing Q{i}...")
            
            # Extract Data
            q_obj = {"id": i}
            
            # Text
            try:
                q_el = await frame.query_selector(".question") or await frame.query_selector(".question-text")
                if q_el:
                    q_obj["text"] = await q_el.inner_text()
                    q_obj["html"] = await q_el.inner_html()
                else:
                    q_obj["text"] = "Text not found"
            except:
                q_obj["text"] = "Error extracting text"

            # Options
            try:
                opts = await frame.query_selector_all(".answer-text")
                q_obj["options"] = [(await o.inner_text()).strip() for o in opts]
            except:
                q_obj["options"] = []

            # Images
            # Logic: Find images in question container
            # Save Base64 to file
            try:
                imgs = await frame.query_selector_all(".question img")
                img_paths = []
                for idx, img in enumerate(imgs):
                    src = await img.get_attribute("src")
                    if "base64" in src:
                        # Decode and save
                        header, encoded = src.split(",", 1)
                        data = base64.b64decode(encoded)
                        filename = f"q{i}_img{idx}.png"
                        filepath = IMAGES_DIR / filename
                        with open(filepath, "wb") as f:
                            f.write(data)
                        img_paths.append(str(filename)) # Relative to images dir
                    else:
                        img_paths.append(src)
                q_obj["images"] = img_paths
            except Exception as e:
                print(f"Image extraction error: {e}")
                q_obj["images"] = []

            questions_data.append(q_obj)

            # Click Answer 'A'
            try:
                # Find first option
                await frame.locator(".answer-text").first.click()
                await asyncio.sleep(0.2)
                
                # Click Next
                # If Q10, we might see "Finish" or just stop loops
                if i < 10:
                    await frame.locator(".next-button").click()
                    await asyncio.sleep(1) # Animation wait
            except Exception as e:
                print(f"Navigation error Q{i}: {e}")

        # 3. Submit
        print("Submitting test...")
        try:
             # "Mark Test"
             await frame.get_by_text("Mark Test").click()
             await asyncio.sleep(1)
             # Confirm dialog
             await frame.locator("button.dialog-confirm-btn").click() # Adjust selector if needed
             await asyncio.sleep(2)
             # "Review my answers"
             await frame.get_by_text("Review my answers").click()
             await asyncio.sleep(2)
        except Exception as e:
            print(f"Submission error: {e}")
            await browser.close()
            return

        # 4. Phase 2: Review & Extract Answers
        print("Starting Phase 2: Review...")
        for i in range(1, 11):
            print(f"Reviewing Q{i}...")
            # Click nav square
            try:
                await frame.locator(f".nav-square >> text={i}").click()
                await asyncio.sleep(1)
            except:
                pass
            
            # Find matching question in our data
            q_data = next((q for q in questions_data if q["id"] == i), None)
            if not q_data:
                continue

            # Extract Explanation
            try:
                # Based on subagent: .review-answer-label or .answer-state parent
                expl_label = await frame.query_selector(".answer-state")
                if expl_label:
                    # Parent text has the whole thing
                    # Need to be careful getting parent handle
                    # Playwright: locator("..")
                    parent = frame.locator(".answer-state").locator("..")
                    full_text = await parent.inner_text()
                    q_data["explanation"] = full_text.strip()
                    
                    # Correct Answer from text
                    match = re.search(r"The answer is ([a-e])", full_text, re.IGNORECASE)
                    if match:
                        q_data["correct_answer"] = match.group(1).lower()
                
                # Fallback: Green button
                if "correct_answer" not in q_data:
                     correct_btn = await frame.query_selector(".answer-text.correct")
                     if correct_btn:
                         txt = await correct_btn.inner_text()
                         q_data["correct_answer"] = txt.strip()[0].lower() # "a) ..." -> "a"

            except Exception as e:
                print(f"Review extraction error Q{i}: {e}")

        # Save Result
        with open(RAW_OUTPUT, "w") as f:
            json.dump(questions_data, f, indent=2)
        
        print(f"Done. Saved to {RAW_OUTPUT}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(crawl())
