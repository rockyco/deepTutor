
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
        # Using a distinct context to ensure clean state and set User-Agent
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print(f"Navigating to {URL}...")
        await page.goto(URL, timeout=60000)
        
        # 1. Access the Iframe
        # The iframe contains the dashboard and tests.
        print("Waiting for application iframe...")
        
        # Robust wait for the iframe element
        try:
             # Wait for the iframe to be attached to DOM
             await page.wait_for_selector("iframe[src*='ElevenPlusOnline']", timeout=30000)
        except:
             print("Timeout waiting for iframe selector.")
             await page.screenshot(path="debug_iframe_timeout.png")
             await browser.close()
             return

        frame = None
        # It might take a moment to be available in page.frames after attachment
        for attempt in range(10):
            for f in page.frames:
                if "ElevenPlusOnline" in f.url:
                    frame = f
                    break
            if frame:
                break
            await asyncio.sleep(1)
            
        if not frame:
            print("Iframe element found but frame object not in page.frames.")
            # Last ditch: try to get the frame from the handle
            element_handle = await page.query_selector("iframe[src*='ElevenPlusOnline']")
            frame = await element_handle.content_frame()
            if not frame:
                print("Could not get content_frame.")
                await browser.close()
                return

        print(f"Found frame: {frame.url}")

        # 2. Select Maths Test INSIDE the iframe
        print("Selecting Maths Test...")
        try:
             await frame.wait_for_load_state("networkidle")
             
             # Use the robust selector from subagent
             # `ul.dashboard-container > li:nth-child(1) button.free-sample-test`
             # Or verify text is GL Maths
             
             # Let's wait for dashboard container
             await frame.wait_for_selector(".dashboard-container", timeout=20000)
             
             # Locate the GL Maths button
             # Subagent said it is the first one.
             # We can also double check text in parent "GL Maths"
             
             # Option 1: Selector
             btn_selector = "ul.dashboard-container > li:nth-child(1) button.free-sample-test"
             
             # Check if this button is for GL Maths
             # We can check the parent text
             # Use .first to avoid strict mode if multiple lists exist
             btn = frame.locator(btn_selector).first
             parent_text = await btn.locator("..").inner_text() 
             print(f"Found button with parent text: {parent_text}")
             
             if "Maths" in parent_text or "GL" in parent_text: # Loose match
                 await btn.click()
             else:
                 print("Parent text didn't match, but trusting subagent that first button is GL Maths.")
                 # We click it anyway as the text might be in a header we didn't check
                 await btn.click()
                 
                 # Fallback code kept for reference but not reached unless click fails
                 # gl_li = frame.locator("li").filter(has_text="GL Maths").first
                 # await gl_li.locator("button.free-sample-test").first.click()

        except Exception as e:
             print(f"Failed to select Maths Test: {e}")
             await page.screenshot(path="debug_select_test.png")
             await browser.close()
             return

        # Wait for the Question 1 to appear
        print("Waiting for Question 1...")
        try:
             await frame.wait_for_selector(".question", timeout=20000)
        except:
             print("Question 1 did not load (timeout).")
             await page.screenshot(path="debug_q1_timeout.png")
             await browser.close()
             return

        questions_data = []

        # 3. Phase 1: Answer All Questions
        print("Starting Phase 1: Answering...")
        for i in range(1, 11):
            valid_q = False
            
            # Wait a bit for transition
            await asyncio.sleep(1)
            
            print(f"Processing Q{i}...")
            
            # Extract Data
            q_obj = {"id": i}
            
            # Text
            try:
                # Try .question-text first as it is more specific
                q_el = await frame.query_selector(".question-text")
                if not q_el:
                    q_el = await frame.query_selector(".question")
                
                if q_el:
                    q_obj["text"] = await q_el.inner_text()
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
            try:
                imgs = await frame.query_selector_all(".question img")
                img_paths = []
                for idx, img in enumerate(imgs):
                    src = await img.get_attribute("src")
                    if src.startswith("data:image"):
                         # Decode and save
                        try:
                            header, encoded = src.split(",", 1)
                            data = base64.b64decode(encoded)
                            filename = f"q{i}_img{idx}.png"
                            filepath = IMAGES_DIR / filename
                            with open(filepath, "wb") as f:
                                f.write(data)
                            img_paths.append(str(filename))
                        except:
                            pass
                    else:
                        img_paths.append(src)
                q_obj["images"] = img_paths
            except Exception as e:
                print(f"Image extraction error: {e}")
                q_obj["images"] = []

            questions_data.append(q_obj)

            # Save partial data just in case
            with open(BASE_DIR / "partial_crawl.json", "w") as f:
                json.dump(questions_data, f, indent=2)

            # Click Answer 'A'
            try:
                # Find first option
                await frame.locator(".answer-text").first.click()
                await asyncio.sleep(0.2)
                
                # Click Next
                if i < 10:
                    await frame.locator(".next-button").click()
            except Exception as e:
                print(f"Navigation error Q{i}: {e}")

        # 3. Submit
        print("Submitting test...")
        try:
             # Check for cookie banner and close it if possible
             print("Checking for cookie banner...")
             try:
                 # Try multiple strategies for cookie banner
                 # Strategy 1: Text
                 cookie_accept = page.get_by_text("Accept all", exact=True)
                 if await cookie_accept.count() > 0:
                     await cookie_accept.click()
                     print("Clicked 'Accept all' cookie banner.")
                 else:
                     # Strategy 2: ID
                     cookie_btn = page.locator("#onetrust-accept-btn-handler")
                     if await cookie_btn.count() > 0:
                         await cookie_btn.click()
                         print("Clicked cookie banner via ID.")
             except Exception as e:
                 print(f"Cookie banner error: {e}")

             await asyncio.sleep(5)
             
             # Loop to attempt submission
             for attempt in range(3):
                 print(f"Submission Attempt {attempt+1}...")
                 # Check if we are on results page
                 if await frame.get_by_text("Review my answers").count() > 0:
                     break
                 
                 # Check if dialog is open
                 if await frame.get_by_text("Are you ready to finish").count() == 0:
                     print("Dialog not open. Clicking Mark Test (Bottom)...")
                     # Try to find the bottom button specifically
                     # It has class dashboard-group-button or similar? No, the screenshot shows just "Mark Test".
                     # I will iterate all Mark Test buttons and click them if they look like the bottom one.
                     mark_btns = frame.get_by_text("Mark Test").all()
                     clicked = False
                     for btn in await mark_btns:
                         if await btn.is_visible():
                             # Use dispatch click which is more robust for angular
                             await btn.dispatch_event("click")
                             clicked = True
                     
                     if not clicked:
                         print("Could not find any visible Mark Test button to click.")
                     
                     await asyncio.sleep(3)
                 
                 # Now try to click confirm in dialog
                 # Find dialog via unique text "Are you ready to finish"
                 dialog_text = frame.get_by_text("Are you ready to finish")
                 if await dialog_text.count() > 0:
                     print("Dialog text found. Locating confirm button...")
                     # Parent of text contains the button
                     parent = dialog_text.locator("..").locator("..")
                     
                     # Look for button inside this parent
                     match_btn = parent.locator("button").filter(has_text="Mark Test").first
                     if await match_btn.count() > 0:
                         print("Found Mark Test button in dialog via text context.")
                         await match_btn.click(force=True)
                         # Also try JS click to be safe
                         await match_btn.evaluate("el => el.click()")
                     else:
                         print("Button not found in dialog context.")
                 else:
                     print("Dialog text not found (unexpected if we just opened it).")
                     # Fallback to dialog-confirm-btn class
                     dialog_btn = frame.locator("button.dialog-confirm-btn").first
                     if await dialog_btn.count() > 0:
                         await dialog_btn.click(force=True)
                 
                 await asyncio.sleep(5)

             # "Review my answers"
             print("Waiting for 'Review my answers'...")
             review_btn = frame.get_by_text("Review my answers")
             await review_btn.wait_for(state="visible", timeout=30000)
             await review_btn.click()
             await asyncio.sleep(2)

        except Exception as e:
             print(f"Submission error: {e}")
             await page.screenshot(path="debug_submit_failure.png")
             await browser.close()
             return

        # 4. Phase 2: Review & Extract Answers
        print("Starting Phase 2: Review...")
        
        for i in range(1, 11):
            print(f"Reviewing Q{i}...")
            # Click nav square
            try:
                await frame.locator(f".nav-square").nth(i-1).click()
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Nav error review Q{i}: {e}")
            
            # Find matching question in our data
            q_data = next((q for q in questions_data if q["id"] == i), None)
            if not q_data:
                continue

            # Extract Explanation
            try:
                # Looking for parent of .answer-state or similar
                expl_container = None
                
                # Try finding the red/green label area
                state_label = frame.locator(".answer-state")
                if await state_label.count() > 0:
                    expl_container = state_label.locator("..")
                    
                    full_text = await expl_container.inner_text()
                    q_data["explanation"] = full_text.strip()
                    
                    # Extract Answer Letter
                    match = re.search(r"The answer is ([a-e])", full_text, re.IGNORECASE)
                    if match:
                        q_data["correct_answer"] = match.group(1).upper()
                    else:
                        print(f"Could not parse 'The answer is X' from text: {full_text[:50]}...")
                else:
                    print(f"Explanation label not found for Q{i}")

                # Fallback: Green button check if we didn't find text
                if "correct_answer" not in q_data:
                     correct_btn = await frame.query_selector(".answer-text.correct")
                     if correct_btn:
                         txt = await correct_btn.inner_text()
                         q_data["correct_answer"] = txt.strip()[0].upper()

            except Exception as e:
                print(f"Review extraction error Q{i}: {e}")

        # Save Result
        with open(RAW_OUTPUT, "w") as f:
            json.dump(questions_data, f, indent=2)
        
        print(f"Done. Saved to {RAW_OUTPUT}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(crawl())
