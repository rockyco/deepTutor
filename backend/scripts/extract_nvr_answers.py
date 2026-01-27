
import asyncio
from playwright.async_api import async_playwright
import json
from pathlib import Path

# Constants
CGP_URL = "https://www.cgpbooks.co.uk/CGPBooks/media/Applications/ElevenPlusOnline_FreeSample_20241220/index.html"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "images" / "granular" / "nvr_answers.json"

async def extract_answers():
    async with async_playwright() as p:
        # Launch browser (headless=False to see what's happening)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()

        print(f"Navigating to {CGP_URL}")
        await page.goto(CGP_URL)

        # 1. Start NVR Test
        print("Looking for Non-Verbal Reasoning test...")
        # Wait for iframe logic or content to load if necessary, but here it seems direct
        # Click the button with text containing "Non-Verbal Reasoning"
        # We look for a parent div that contains the text, then the button/link
        try:
            # Wait for any "Free sample test" button
            await page.wait_for_selector("text=Free sample test", timeout=10000)
            
            # Find all "Free sample test" buttons
            buttons = await page.get_by_text("Free sample test").all()
            
            nvr_button = None
            for btn in buttons:
                # Check parent text for "Non-Verbal Reasoning"
                # Go up to a container that might have the title
                parent = await btn.locator("xpath=../../..").text_content()
                if "Non-Verbal Reasoning" in parent:
                    nvr_button = btn
                    break
            
            if nvr_button:
                await nvr_button.click()
            else:
                print("Could not find specific NVR button, trying 4th button as fallback...")
                await buttons[3].click() # Fallback based on previous observation
                
        except Exception as e:
            print(f"Error finding button: {e}")
            await browser.close()
            return

        # 2. Answer all questions (Option A) to get to the end
        print("Answering questions...")
        
        for q_num in range(1, 6): # 5 questions
            print(f"Processing Q{q_num}...")
            # Use nav squares if we are not on the right question (auto-advance might valid)
            # But let's just use nav squares to be sure
            nav_squares = page.locator(".nav-square")
            try:
                await nav_squares.nth(q_num - 1).click(timeout=5000)
            except:
                print("Nav square not found or clickable, proceeding...")

            await page.wait_for_timeout(1000)
            
            # Click Option A
            # Strategy: Click the image associated with "a)"
            # Or just click the first option container
            # We will try to find images
            images = await page.locator("img[src^='data:image']").all()
            if len(images) >= 5:
                # If >= 6, index 0 is main, index 1 is A.
                # If 5, index 0 is A.
                click_index = 0
                if len(images) >= 6:
                    click_index = 1
                
                try:
                    await images[click_index].click(timeout=2000)
                except:
                    # Fallback: maybe click a radio button input
                    radios = await page.locator("input[type='radio']").all()
                    if radios:
                        await radios[0].click()
            else:
                print(f"Could not find option images for Q{q_num}")

        # Click Mark Test (usually at bottom right, or via menu)
        print("Submitting test...")
        mark_btn = page.get_by_text("Mark Test")
        if await mark_btn.count() > 0:
            await mark_btn.click()
        else:
            # Maybe inside a button
            await page.locator("button:has-text('Mark Test')").click()

        # 3. Handle Confirmation Popup
        print("Confirming submission...")
        await page.wait_for_timeout(1000)
        # Verify if popup appeared
        confirm_btn = page.locator(".modal-footer >> text=Mark Test")
        if await confirm_btn.count() > 0:
            await confirm_btn.click()
        else:
            # Try finding the popup button generically
            btns = page.locator("button:has-text('Mark Test')")
            # The second one might be the popup one if the main one is still visible
            if await btns.count() > 1:
                await btns.nth(1).click()

        # 4. Results Page
        print("Waiting for results...")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(5) 

        # Scan for 'Review Answers' or similar
        content = await page.content()
        if "Review Answers" in content:
            await page.get_by_text("Review Answers").click()
        elif "Review" in content:
             await page.get_by_text("Review").click()
        
        await asyncio.sleep(2)

        # 5. Extract Answers
        answers = {}
        
        # Navigate through questions again
        for q_num in range(1, 6):
            print(f"Extracting answer for Q{q_num}...")
            
            nav_squares = page.locator(".nav-square")
            await nav_squares.nth(q_num - 1).click()
            await page.wait_for_timeout(1000)
            
            # Look for correct answer indicator
            # Often a class "correct" on the parent div of the option
            # Or a specific icon
            
            # Dump HTML snippet if unsure
            # But let's look for .correct class
            correct_found = False
            option_letters = ["A", "B", "C", "D", "E"]
            
            # Check for elements with 'correct' class
            correct_elements = page.locator(".correct")
            if await correct_elements.count() > 0:
                # Find which option this is inside
                # This might be hard if .correct is deep
                # Let's iterate options and check class
                
                # Assuming options are identifiable containers
                # We can try to match the "correct" class to an index
                
                # Check option containers logic again
                # In many 11+ apps, the correct option gets a green border or background
                # Class might be "answer-option correct" or style "background-color: ..."
                
                pass
            
            # Strategy: Search for text "Correct Answer: X" logic if present
            # Strategy: Check inputs
            
            # Let's try locating inputs and checking if they have a 'correct' class or sibling
            inputs = await page.locator("input[type='radio']").all()
            for i, inp in enumerate(inputs):
                # Check parent class
                parent = inp.locator("..") # Parent element
                class_attr = await parent.get_attribute("class") or ""
                if "correct" in class_attr.lower():
                     answers[str(q_num)] = option_letters[i]
                     correct_found = True
                     break
            
            if not correct_found:
                 # Check for "tick" icon images
                 ticks = page.locator("img[src*='tick'], .fa-check") 
                 if await ticks.count() > 0:
                     # Locate which option container has the tick
                     # This is tricky without precise structure
                     # Let's save a "Unknown" and dump HTML for debugging this specific q
                     answers[str(q_num)] = "Unknown"
                     print(f"Found tick usage but couldn't map to option (needs debug)")
                 else:
                     answers[str(q_num)] = "Unknown"
        
        print(f"Extracted Answers: {answers}")
        
        # Save extracted answers
        with open(OUTPUT_FILE, "w") as f:
            json.dump(answers, f, indent=2)
            
        print(f"Saved answers to {OUTPUT_FILE}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(extract_answers())
