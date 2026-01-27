import asyncio
import base64
import json
import os
import re
from playwright.async_api import async_playwright

OUTPUT_DIR = "backend/data/images/granular"
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def extract_images():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use a context to ensure clean state
        context = await browser.new_context()
        page = await context.new_page()

        print("Navigating to CGP App directly...")
        # Direct URL found from subagent logs
        await page.goto("https://www.cgpbooks.co.uk/CGPBooks/media/Applications/ElevenPlusOnline_FreeSample_20241220/")
        
        # Wait for the "Free sample test" buttons
        # The structure likely has buttons for Maths, English, NVR, VR
        try:
            await page.wait_for_selector(".btn", timeout=15000)
            # Or search for text
        except:
            pass

        # Find all buttons with "Free sample test" text
        # Sometimes they are images or divs with onClick.
        # Let's try locating by text "Non-Verbal Reasoning"
        
        nvr_text = page.locator("text=Non-Verbal Reasoning")
        if await nvr_text.count() > 0:
            print("Found NVR text, looking for button nearby...")
            # Click the button that is likely a sibling or child
            # Try clicking the "Free sample test" button inside the NVR container
            # Assuming typical card layout
            card = nvr_text.first.locator("xpath=..").locator("xpath=..") # Go up to card
            btn = card.locator("text=Free sample test").first
            if await btn.count() > 0:
                await btn.click()
            else:
                # Fallback: click simple "Free sample test" if NVR text is unique enough
                # Or maybe the text itself is clickable?
                await nvr_text.first.click()
        else:
             print("NVR Text not found. Dumping page text...")
             # content = await page.inner_text("body") 
             # print(content[:500])
             
             # Fallback coordinates or assuming order
             # If we see 4 "Free sample test" buttons, NVR is usually 4th?
             buttons = page.locator("text=Free sample test")
             if await buttons.count() >= 4:
                 await buttons.nth(3).click()
             else:
                 print(f"Found {await buttons.count()} buttons. Clicking last one.")
                 if await buttons.count() > 0:
                     await buttons.last.click()
        
        print("Waiting for test to load...")
        # Dictionary to store metadata
        metadata = []

        # Iterate 5 questions
        for q_idx in range(1, 6):
            print(f"Processing Question {q_idx}...")
            
            # Wait for "Question X" or just wait for the image to be present
            try:
                # The page might be an iframe? Previous logs showed an iframe src:
                # https://www.cgpbooks.co.uk/CGPBooks/media/Applications/ElevenPlusOnline_FreeSample_20241220/
                # Playwright handles iframes automatically if we search in frames, but better to check.
                
                # Check for iframe
                frame = None
                # Wait a bit for iframe to appear
                await page.wait_for_timeout(3000)
                
                for f in page.frames:
                    if "ElevenPlusOnline" in f.url:
                        frame = f
                        break
                
                if not frame:
                    frame = page.main_frame
                
                # Wait for main image or question text
                await frame.wait_for_selector("img", timeout=10000)
                await frame.wait_for_timeout(2000) # Grace period for images to render

                # Extract Data
                data = await frame.evaluate("""
                    () => {
                        const result = {
                            question_text: "",
                            main_image: null,
                            options: []
                        };
                        
                        // Extract Text
                        const bodyText = document.body.innerText;
                        // Match "Question X ... (text)"
                        // Attempt to capture text 
                        result.question_text = bodyText.split('\\n').find(l => l.includes('Question')) || "";
                        
                        // Extract Images
                        const allImages = Array.from(document.querySelectorAll('img')).filter(img => img.width > 20 && img.height > 20 && !img.src.includes('logo'));
                        
                        // Sort by vertical position
                        allImages.sort((a,b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
                        
                        // Assumption: First image is main, subsequent are options?
                        // Or look for answer-text labels
                        
                        const labels = Array.from(document.querySelectorAll('.answer-text, .answer-label'));
                        
                        if (labels.length > 0) {
                            // Find images close to labels
                             labels.forEach(el => {
                                const labelRect = el.getBoundingClientRect();
                                // Find closest image
                                 let bestImg = null;
                                 let minDist = 10000;
                                 
                                 allImages.forEach(img => {
                                     const imgRect = img.getBoundingClientRect();
                                     // Euclidean dist is simple enough, favoring y-proximity?
                                     // Actually options are often: [Image] \n [Label] or [Image] [Label]
                                     const dist = Math.abs(imgRect.left - labelRect.left) + Math.abs(imgRect.top - labelRect.top);
                                     if (dist < minDist && dist < 200) {
                                         minDist = dist;
                                         bestImg = img;
                                     }
                                 });
                                 
                                 if (bestImg) {
                                     result.options.push({
                                         label: el.innerText.trim().replace(/[()]/g, ''),
                                         src: bestImg.src
                                     });
                                 }
                             });
                             
                             // Main image is the one NOT in options
                             const optSrcs = result.options.map(o => o.src);
                             const mainImgs = allImages.filter(img => !optSrcs.includes(img.src));
                             if (mainImgs.length > 0) {
                                 result.main_image = mainImgs[0].src;
                             }
                        } else {
                            // Fallback if no labels found (unlikely for NVR)
                            if (allImages.length > 0) result.main_image = allImages[0].src;
                        }
                        return result;
                    }
                """)
                
                # Save Images
                record = {
                    "id": f"q{q_idx}",
                    "text": data['question_text'],
                    "image_path": None,
                    "option_images": [],
                    "options": []
                }
                
                # Save Main Image
                if data['main_image']:
                    # Expect data:image/png;base64,....
                    if "base64," in data['main_image']:
                        header, encoded = data['main_image'].split("base64,", 1)
                        ext = "png" 
                        if "jpeg" in header: ext = "jpg"
                        
                        fname = f"nvr_q{q_idx}_main.{ext}"
                        with open(f"{OUTPUT_DIR}/{fname}", "wb") as f:
                            f.write(base64.b64decode(encoded))
                        record["image_path"] = f"/images/granular/{fname}"
                        print(f"Saved {fname}")
                
                # Save Options
                for i, opt in enumerate(data['options']):
                    label = opt['label'] or ["a","b","c","d","e"][i]
                    if "base64," in opt['src']:
                        header, encoded = opt['src'].split("base64,", 1)
                        ext = "png"
                        if "jpeg" in header: ext = "jpg"
                        
                        fname = f"nvr_q{q_idx}_opt_{label.lower()}.{ext}"
                        with open(f"{OUTPUT_DIR}/{fname}", "wb") as f:
                            f.write(base64.b64decode(encoded))
                        
                        record["option_images"].append(f"/images/granular/{fname}")
                        record["options"].append(label)
                        print(f"Saved {fname}")
                
                metadata.append(record)

                # Click Next
                # Check for .nav-square
                squares = frame.locator(".nav-square")
                if await squares.count() > q_idx:
                    # Click next square (0-indexed, so q_idx is the *next* one? No squares are 1,2,3..)
                    # Actually squares usually corresponds to Q1, Q2..
                    # So for Q1 (idx 0), we are done. Before loop ends, click next (idx 1).
                    if q_idx < 5:
                        print("Clicking Next...")
                        await squares.nth(q_idx).click() # Click Q(i+1)
                        await page.wait_for_timeout(1000)

            except Exception as e:
                print(f"Error on Q{q_idx}: {e}")
                import traceback
                traceback.print_exc()

        # Save Metadata
        with open(f"{OUTPUT_DIR}/nvr_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
            
        print("Extraction complete.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(extract_images())
