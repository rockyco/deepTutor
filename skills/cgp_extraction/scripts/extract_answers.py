import asyncio
import json
import os
import re
from playwright.async_api import async_playwright

# --- CONFIGURATION ---
# --- CONFIGURATION ---
URL = "https://www.cgpbooks.co.uk/11-plus-free-sample"
SUBJECT_KEY = "non_verbal_reasoning"
OUTPUT_FILE = f"backend/data/images/granular_{SUBJECT_KEY}/answers.json"
# ---------------------

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

async def extract_answers():
    async with async_playwright() as p:
        # Use headless=True for automated runs
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print(f"Navigating to {URL}...")
        await page.goto(URL)
        
        # --- SELECT TEST ---
        print(f"Looking for test button for {SUBJECT_KEY}...")
        
        # Locate iframe
        iframe_element = await page.locator("iframe.display-app-container").element_handle()
        frame = await iframe_element.content_frame()
        
        try:
             # Dismiss cookies if present
             if await page.locator(".cookie-message-content").count() > 0:
                 await page.get_by_text("Accept").click(timeout=2000)
        except:
             pass

        try:
             if SUBJECT_KEY == "non_verbal_reasoning":
                 # Ensure wait
                 await frame.locator(".dashboard-group").first.wait_for(timeout=10000)
                 await frame.locator(".dashboard-group").filter(has_text="GL Non-Verbal Reasoning").locator("button.free-sample-test").click()
             else:
                 # Fallback
                 await frame.locator("button.free-sample-test").nth(1).click()
        except Exception as e:
             print(f"Failed to select test: {e}")
             await browser.close()
             return

        # --- ANSWER QUESTIONS ---
        print("Answering questions...")
        
        # Get Frame (already defined above)
        # frame = page.frame_locator("iframe.display-app-container")
        await frame.locator("#question-content").first.wait_for()

        # Loop until finished
        for i in range(20): # Safety limit
            await page.wait_for_timeout(500)
            
            # Check for End/Mark Test
            if await frame.get_by_text("Mark Test").count() > 0:
                 # Ensure cookies are gone first
                 try:
                     # Target specific Accept All button
                     if await page.get_by_text("Accept all").count() > 0:
                         await page.get_by_text("Accept all").click(timeout=3000)
                     elif await page.locator(".cookie-message-content").count() > 0:
                         await page.locator(".cookie-message-content").get_by_text("Accept").click(timeout=3000)
                 except:
                     pass

                 # Click main Mark Test button
                 await frame.get_by_text("Mark Test").click()
                 await page.wait_for_timeout(2000)
                 
                 # Confirm modal loop
                 # Confirm modal loop
                 for i in range(5):
                     print(f"Confim loop {i+1}...")
                     
                     # 1. Try Frame JS
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
                     
                     # 2. Try Page JS (if modal is outside iframe)
                     if not clicked:
                         print("Not found in frame, checking main page...")
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
                     else:
                         print("No visible confirm button found via JS (frame or page).")
                         # Fallback: maybe it's just 'button' without class?
                         # Try frame fallback
                         await frame.evaluate("""
                            () => {
                                const btns = Array.from(document.querySelectorAll('button'));
                                const target = btns.find(b => b.innerText.trim() === 'Mark Test' && b.offsetParent !== null);
                                if (target && !target.classList.contains('dashboard-group-button')) { 
                                     target.click();
                                }
                            }
                         """)
                         # Try page fallback
                         await page.evaluate("""
                            () => {
                                const btns = Array.from(document.querySelectorAll('button'));
                                const target = btns.find(b => b.innerText.trim() === 'Mark Test' && b.offsetParent !== null);
                                if (target && !target.classList.contains('dashboard-group-button')) { 
                                     target.click();
                                }
                            }
                         """)
                     
                     # Check if review button appeared, if so break
                     if await frame.locator("button").filter(has_text="Review my answers").count() > 0:
                         print("Review button appeared!")
                         break
                     
                     await page.wait_for_timeout(1000)
                 break
            
            # Answer 'A'
            # Answer 'A'
            try:
                # Click first option
                await frame.locator(".input-button").first.click(timeout=1000)
                await page.wait_for_timeout(200)
                # Next
                await frame.locator(".next-button").click(timeout=1000)
            except:
                pass

        # --- REVIEW ---
        print("Entering review mode...")
        try:
            print("Waiting for Review button...")
            # Results page sometimes takes time.
            await frame.locator("button").filter(has_text="Review my answers").wait_for(timeout=20000)
            await frame.locator("button").filter(has_text="Review my answers").click()
        except Exception as e:
            print(f"Review button not found: {e}")
            await page.screenshot(path="debug_review_fail.png")
            await browser.close()
            return

        # --- EXTRACT ---
        answers = {}
        for q_num in range(1, 11):
            print(f"Extracting Q{q_num}...")
            # Navigate to q_num
            try:
                await frame.locator(f".nav-square >> text={q_num}").click()
                await page.wait_for_timeout(1000)
            except:
                pass

            # Extract Explanation Text
            try:
                # The structure is usually within .content-box or .answer-content-area
                # Explanation is typically in a text block showing "Incorrect. The answer is X..."
                # We look for the text containing "The answer is"
                explanation_el = frame.locator(".answer-state").locator("..") # Parent of answer-state label
                full_text = await explanation_el.inner_text()
                
                # Regex for answer
                # Matches "The answer is X" or "The correct answer is X"
                match = re.search(r"The (?:correct )?answer is ([a-e])", full_text, re.IGNORECASE)
                answer_char = match.group(1).upper() if match else "Unknown"
                
                answers[str(q_num)] = {
                    "answer": answer_char,
                    "explanation": full_text.strip()
                }
                print(f"Q{q_num}: {answer_char}")
                
            except Exception as e:
                print(f"Error extraction Q{q_num}: {e}")
                answers[str(q_num)] = {"answer": "Unknown", "explanation": ""}

        with open(OUTPUT_FILE, "w") as f:
            json.dump(answers, f, indent=2)
        print(f"Saved to {OUTPUT_FILE}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(extract_answers())
