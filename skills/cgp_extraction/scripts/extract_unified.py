import asyncio
import base64
import json
import os
import re
import sys
import argparse
import glob
from playwright.async_api import async_playwright


def get_next_question_number(output_dir: str) -> int:
    """Find the highest existing question number and return next available."""
    max_num = 0
    
    # Check existing image files
    for pattern in ["q*_question*.png", "q*_option*.png"]:
        for filepath in glob.glob(f"{output_dir}/{pattern}"):
            filename = os.path.basename(filepath)
            # Extract number from q123_question_0.png
            match = re.match(r'q(\d+)_', filename)
            if match:
                num = int(match.group(1))
                max_num = max(max_num, num)
    
    # Also check metadata.json for question_num values
    metadata_file = f"{output_dir}/metadata.json"
    if os.path.exists(metadata_file):
        try:
            with open(metadata_file) as f:
                existing = json.load(f)
                for q in existing:
                    if 'question_num' in q:
                        max_num = max(max_num, q['question_num'])
        except:
            pass
    
    return max_num + 1

# --- CONFIGURATION MAP ---
SUBJECT_CONFIG = {
    "maths": {
        "ui_text": ["GL Maths", "Maths"],
        "output_dir": "backend/data/images/granular_maths"
    },
    "non_verbal_reasoning": {
        "ui_text": ["GL Non-Verbal Reasoning", "Non-Verbal Reasoning"],
        "output_dir": "backend/data/images/granular_non_verbal_reasoning"
    },
    "verbal_reasoning": {
        "ui_text": ["GL Verbal Reasoning", "Verbal Reasoning"],
        "output_dir": "backend/data/images/granular_verbal_reasoning"
    },
    "english": {
        "ui_text": ["GL English", "English"],
        "output_dir": "backend/data/images/granular_english"
    }
}

URL = "https://www.cgpbooks.co.uk/11-plus-free-sample"

async def extract_unified(subject_key: str):
    config = SUBJECT_CONFIG.get(subject_key)
    if not config:
        print(f"Error: Unknown subject '{subject_key}'. Available: {list(SUBJECT_CONFIG.keys())}")
        return

    output_dir = config["output_dir"]
    metadata_file = f"{output_dir}/metadata.json"
    os.makedirs(output_dir, exist_ok=True)
    
    # Get starting question number (for accumulation)
    start_q_num = get_next_question_number(output_dir)
    
    print(f"Starting Extraction for: {subject_key}")
    print(f"Output Directory: {output_dir}")
    print(f"Starting from question number: {start_q_num}")

    async with async_playwright() as p:
        # Use headless=True for stability in this environment
        # Add anti-bot detection args
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Add script to mask webdriver
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

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
        try:
             iframe_element = await page.locator("iframe.display-app-container").element_handle(timeout=30000)
             frame = await iframe_element.content_frame()
        except Exception as e:
             print(f"Error finding iframe: {e}")
             await page.screenshot(path="debug_iframe_timeout.png")
             await browser.close()
             return

        # Start Test
        print(f"Selecting test...")
        started = False
        try:
             await frame.locator(".dashboard-group").first.wait_for(timeout=10000)
             
             # Try identifiers in order
             for identifier in config["ui_text"]:
                 group = frame.locator(".dashboard-group").filter(has_text=identifier)
                 if await group.count() > 0:
                     print(f"Found group for '{identifier}'")
                     await group.locator("button.free-sample-test").click()
                     started = True
                     break
             
             if not started:
                 print(f"Could not find test button for {subject_key}")
                 # Fallback: Capture screenshot
                 await page.screenshot(path="debug_unified_start_fail.png")
                 await browser.close()
                 return
                 
        except Exception as e:
             print(f"Failed to start test: {e}")
             await browser.close()
             return

        await frame.locator("#question-content").first.wait_for(timeout=20000)
        
        # --- PHASE 1: EXTRACT IMAGES & SUBMIT ANSWERS ---
        print("--- PHASE 1: Image Extraction & Submission ---")
        
        questions_map = {} # Key: q_num, Value: dict
        
        # Determine number of questions (heuristic, stop when navigation fails or loop limit)
        session_q_count = 0
        for nav_idx in range(1, 16):
            q_num = start_q_num + session_q_count
            print(f"Processing Q{q_num} (session #{nav_idx})...")
            
            # 1. Navigation
            # If not first question, click nav square
            if nav_idx > 1:
                try:
                    nav_square = frame.locator(f".nav-square >> text={nav_idx}")
                    # If nav square doesn't exist, we might be done
                    if await nav_square.count() == 0:
                        print(f"No navigation square for #{nav_idx}. Stopping phase 1 loop.")
                        break
                    
                    await nav_square.click()
                    await page.wait_for_timeout(1000)
                except:
                    print(f"Navigation failed for #{nav_idx}. Stopping.")
                    break
            
            # Check if this is the end (Summary page?)
            if await frame.locator(".result-score-container").count() > 0:
                 break

            # 2. Extract Text & Passages
            text_data = await frame.evaluate("""
                () => {
                    const qContent = document.querySelector('#question-content');
                    let mainText = qContent ? qContent.innerText.trim() : "";
                    
                    // CLEANUP: Strip "See example" which is UI text
                    mainText = mainText.replace(/See example/gi, "").trim();

                    // Check for passage/extract (mostly English)
                    const extractContainer = document.querySelector('.extract-container');
                    let passageText = "";
                    if (extractContainer && extractContainer.offsetParent !== null) { // if visible
                         passageText = extractContainer.innerText.trim();
                    }
                    
                    return { main: mainText, passage: passageText };
                }
            """)
            
            final_text = text_data["main"]
            
            # CLEANUP: Fix known fraction scrambling (e.g. "2\n2\n1" -> "2 1/2")
            # Heuristic: Whole Denom Num -> Whole Num/Denom
            import re
            final_text = re.sub(r'(\d+)\s+(\d+)\s+(\d+)\s+hours', r'\1 \3/\2 hours', final_text)

            # If passage exists...
            if text_data["passage"]:
                 final_text = f"PASSAGE:\n{text_data['passage']}\n\nQUESTION:\n{final_text}"

            # DEBUG: Hunt for the Fraction Question (Rui)
            if "Rui" in final_text or "holiday club" in final_text:
                print(f"!!! FOUND TARGET QUESTION at Q{q_num} !!!")
                html_structure = await frame.evaluate("document.querySelector('#question-content').outerHTML")
                with open(f"{output_dir}/debug_rui_fraction.html", "w") as f:
                    f.write(html_structure)

            # ... [Lines 156-237 omitted for brevity in this replace block, need to be careful with context]
            # Actually, I should split this into two chunks if they are far apart.
            # But I can't easily do that without rewriting the middle.
            # I will use multi_replace.


            # 3. Extract Images (Robust)
            # 3. Extract Images (Robust Segregation)
            images_data = await frame.evaluate("""
                () => {
                    const qContainer = document.querySelector('#question-content');
                    // Find ALL images in question container
                    const qImages = qContainer ? Array.from(qContainer.querySelectorAll('img')) : [];
                    
                    const questionImageSrcs = qImages
                        .filter(img => img.src.startsWith('data:image'))
                        .map(img => img.src);

                    // Options images: Strictly look inside answer containers
                    // CGP structure: .answer-content or .keyboard-key (for NVR)
                    const optionContainers = document.querySelectorAll('.answer-content, .keyboard-key, .option-container, .answer-container, .answer-item, .param-container');
                    let optionImageSrcs = [];
                    
                    optionContainers.forEach(container => {
                        const imgs = Array.from(container.querySelectorAll('img'));
                        imgs.forEach(img => {
                            if (img.src.startsWith('data:image') && !qImages.includes(img)) {
                                optionImageSrcs.push(img.src);
                            }
                        });
                    });
                    
                    // Fallback: If no strict option images found, look for all other images NOT in question
                    if (optionImageSrcs.length === 0) {
                         // console.log("Fallback: No option images found in standard containers.");
                         const allImages = Array.from(document.querySelectorAll('img'));
                         optionImageSrcs = allImages
                            .filter(img => !qImages.includes(img) && img.src.startsWith('data:image') && img.closest('.answer-area'))
                            .map(img => img.src);
                    }

                    return {
                        question_images: questionImageSrcs,
                        option_images: optionImageSrcs
                    };
                }
            """)
            
            q_data = {
                "question_num": q_num,
                "text": final_text,
                "question_image": None, # Kept for backward compat, will hold first image
                "question_images": [], # New field for multiple
                "images": [],
                "answer": "Unknown", 
                "explanation": ""
            }

            # Save Question Images
            if images_data['question_images']:
                # Save all, set first as legacy 'question_image'
                for idx, src in enumerate(images_data['question_images']):
                    b64 = src.split(',')[1]
                    filename = f"q{q_num}_question_{idx}.png"
                    filepath = f"{output_dir}/{filename}"
                    with open(filepath, "wb") as f:
                        f.write(base64.b64decode(b64))
                    q_data["question_images"].append(filename)
                
                if q_data["question_images"]:
                    q_data["question_image"] = q_data["question_images"][0]

            # Save Option Images
            for i, src in enumerate(images_data['option_images']):
                b64 = src.split(',')[1]
                filename = f"q{q_num}_option_{i}.png"
                filepath = f"{output_dir}/{filename}"
                with open(filepath, "wb") as f:
                    f.write(base64.b64decode(b64))
                q_data["images"].append(filename)
            
            # Store options text (Robust for Maths/VR/English)
            option_texts = await frame.evaluate("""
                () => {
                    return Array.from(document.querySelectorAll('.answer-text'))
                        .filter(el => el.offsetParent !== null) // Ignore hidden/modal elements
                        .map(label => {
                            let fullText = label.innerText.trim();
                            return fullText.replace(/^[A-E][.).]?\s+/i, "").trim();
                        });
                }
            """)
            if option_texts and any(t for t in option_texts):
                q_data["options"] = option_texts
            

            questions_map[q_num] = q_data
            session_q_count += 1
            
            # 4. Select an Answer (Option A)
            try:
                # Try image-based input buttons first
                await frame.locator(".input-button").first.click(timeout=1000)
                await page.wait_for_timeout(200)
            except:
                pass
                
        # --- SUBMISSION ---
        print("Submitting test...")
        # Often "Mark Test" is visible.
        if await frame.get_by_text("Mark Test").count() > 0:
             await frame.get_by_text("Mark Test").click()
             await page.wait_for_timeout(2000)
             
             # Confirm modal loop (Robust JS)
             for i in range(5):
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
        
        # Iterate over Keys in map to ensure we check specific questions we processed
        for q_num in questions_map.keys():
            print(f"Extracting Answer Q{q_num}...")
            # Navigate
            try:
                await frame.locator(f".nav-square >> text={q_num}").click()
                await page.wait_for_timeout(1000)
            except:
                pass

            # Extract Explanation & Answer Text Match
            try:
                explanation_el = frame.locator(".answer-state").locator("..")
                full_text = await explanation_el.inner_text()
                
                # Capture the ACTUAL text of correct answers from the DOM
                correct_texts = await frame.evaluate("""
                    () => {
                        const correctLabels = Array.from(document.querySelectorAll('.answer-text.correct, .answer-text.correct-answer'))
                            .filter(el => el.offsetParent !== null);
                        
                        return correctLabels.map(el => {
                            let text = el.innerText.trim();
                            // Strip prefix "A)", "B." etc to get raw text
                            return text.replace(/^[A-E][.).]?\s+/i, "").trim();
                        });
                    }
                """)
                
                # Match against stored options from Phase 1
                stored_options = questions_map[q_num].get("options", [])
                matched_chars = []
                
                if not correct_texts and "answer is" in full_text:
                     # Fallback to regex if no highlighted elements (rare)
                     # But basic regex is brittle. Prefer text match if possible.
                     pass

                for c_text in correct_texts:
                    # Clean comparison
                    c_clean = c_text.lower()
                    best_idx = -1
                    best_ratio = 0
                    
                    # Exact or Substring match
                    for i, opt in enumerate(stored_options):
                        o_clean = opt.lower()
                        if c_clean == o_clean:
                            best_idx = i
                            break
                        # Fallback: if 'be' vs 'be '
                        if c_clean in o_clean or o_clean in c_clean:
                             # Check length ratio to avoid "cat" matching "catch"
                             if len(c_clean) > 0 and len(o_clean) > 0:
                                 ratio = min(len(c_clean), len(o_clean)) / max(len(c_clean), len(o_clean))
                                 if ratio > 0.8: # Good overlap
                                     best_idx = i
                    
                    if best_idx != -1:
                        matched_chars.append(chr(65 + best_idx))
                    else:
                        # Fallback: check if c_clean is just a letter (a, b, c...)
                        letter_match = re.match(r'^([a-e])[.)]?$', c_clean)
                        if letter_match:
                             letter = letter_match.group(1).upper()
                             matched_chars.append(letter)
                        else:
                             print(f"Warning: Could not match answer text '{c_text}' to options {stored_options}")

                if matched_chars:
                    answer_char = ", ".join(sorted(set(matched_chars)))
                else:
                    answer_char = "Unknown"

                # If still unknown and we have options, maybe try to match the explanation text?
                if answer_char == "Unknown" and "The answer is" in full_text:
                     match = re.search(r"The (?:correct )?answer is ([A-E])", full_text, re.IGNORECASE)
                     if match:
                         answer_char = match.group(1).upper()

                questions_map[q_num]["answer"] = answer_char
                questions_map[q_num]["explanation"] = full_text.strip()
                print(f"Q{q_num}: {answer_char} (Matched '{correct_texts}' => {matched_chars})")
            except Exception as e:
                print(f"Error extraction Q{q_num}: {e}")
        # --- SAVE ---
        # --- SAVE (APPEND MODE) ---
        new_questions = list(questions_map.values())
        
        existing_metadata = []
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file) as f:
                    existing_metadata = json.load(f)
            except:
                pass
        
        all_metadata = existing_metadata + new_questions
        
        with open(metadata_file, "w") as f:
            json.dump(all_metadata, f, indent=2)
            
        print(f"Saved complete metadata to {metadata_file} (Added {len(new_questions)} questions)")
        await browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract content for a specific subject.")
    parser.add_argument("--subject", required=True, help="Subject key (maths, non_verbal_reasoning, verbal_reasoning, english)")
    args = parser.parse_args()
    
    asyncio.run(extract_unified(args.subject))
