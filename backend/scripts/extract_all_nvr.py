import asyncio
import base64
import json
import os
from playwright.async_api import async_playwright

OUTPUT_DIR = "backend/data/images/granular"
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def extract_all_nvr():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("1. Navigating to CGP App...")
        await page.goto("https://www.cgpbooks.co.uk/CGPBooks/media/Applications/ElevenPlusOnline_FreeSample_20241220/")
        await page.wait_for_timeout(3000)
        
        print("2. Clicking NVR 'Free sample test' button...")
        buttons = page.locator("text=Free sample test")
        await buttons.nth(2).click()  # NVR is 3rd button (index 2)
        await page.wait_for_timeout(3000)
        
        # Metadata for all questions
        all_metadata = []
        
        # Extract 5 questions
        for q_num in range(1, 6):
            print(f"\n--- Question {q_num} ---")
            
            # Navigate to question if not first
            if q_num > 1:
                # Click the question number in navigation
                nav_squares = page.locator(".nav-square")
                await nav_squares.nth(q_num - 1).click()
                await page.wait_for_timeout(2000)
            
            # Take screenshot
            await page.screenshot(path=f"{OUTPUT_DIR}/nvr_q{q_num}_screenshot.png")
            
            # Extract question text
            question_text = await page.evaluate("""
                () => {
                    const bodyText = document.body.innerText;
                    const match = bodyText.match(/Question \\d+\\s+([\\s\\S]+?)(?=\\s*See example|\\s*[a]\\)|$)/);
                    return match ? match[1].trim().split('\\n')[0] : '';
                }
            """)
            print(f"   Text: {question_text[:50]}...")
            
            # Extract images
            images_data = await page.evaluate("""
                () => {
                    const images = Array.from(document.querySelectorAll('img')).filter(img => img.src.startsWith('data:image'));
                    return images.map((img, i) => ({
                        index: i,
                        src: img.src
                    }));
                }
            """)
            
            print(f"   Found {len(images_data)} images")
            
            # Save images
            q_metadata = {
                "question_num": q_num,
                "text": question_text,
                "main_image": None,
                "option_images": [],
                "options": ["A", "B", "C", "D", "E"]
            }
            
            labels = ['a', 'b', 'c', 'd', 'e']
            
            if len(images_data) >= 6:
                # Has main image + 5 options
                for i, img_data in enumerate(images_data[:6]):
                    src = img_data['src']
                    if src.startswith('data:image'):
                        b64 = src.split(',')[1]
                        
                        if i == 0:
                            filename = f"nvr_q{q_num}_main.png"
                            q_metadata["main_image"] = f"/images/granular/{filename}"
                        else:
                            filename = f"nvr_q{q_num}_opt_{labels[i-1]}.png"
                            q_metadata["option_images"].append(f"/images/granular/{filename}")
                        
                        filepath = f"{OUTPUT_DIR}/{filename}"
                        with open(filepath, "wb") as f:
                            f.write(base64.b64decode(b64))
                        print(f"   Saved: {filename}")
            
            elif len(images_data) == 5:
                # Only options (no main image for "odd one out" type)
                for i, img_data in enumerate(images_data):
                    src = img_data['src']
                    if src.startswith('data:image'):
                        b64 = src.split(',')[1]
                        filename = f"nvr_q{q_num}_opt_{labels[i]}.png"
                        q_metadata["option_images"].append(f"/images/granular/{filename}")
                        
                        filepath = f"{OUTPUT_DIR}/{filename}"
                        with open(filepath, "wb") as f:
                            f.write(base64.b64decode(b64))
                        print(f"   Saved: {filename}")
            
            else:
                print(f"   WARNING: Unexpected image count: {len(images_data)}")
            
            all_metadata.append(q_metadata)
        
        # Save metadata
        with open(f"{OUTPUT_DIR}/nvr_metadata.json", "w") as f:
            json.dump(all_metadata, f, indent=2)
        
        print("\n=== Extraction Complete ===")
        print(f"Metadata saved to {OUTPUT_DIR}/nvr_metadata.json")
        
        await browser.close()
        return all_metadata

if __name__ == "__main__":
    asyncio.run(extract_all_nvr())
