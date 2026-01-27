import asyncio
import base64
import os
from playwright.async_api import async_playwright

OUTPUT_DIR = "backend/data/images/granular"
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def extract_q1():
    async with async_playwright() as p:
        # Launch visible browser for debugging
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("1. Navigating to CGP App...")
        await page.goto("https://www.cgpbooks.co.uk/CGPBooks/media/Applications/ElevenPlusOnline_FreeSample_20241220/")
        await page.wait_for_timeout(3000)
        
        print("2. Looking for NVR 'Free sample test' button...")
        # Find GL Non-Verbal Reasoning section and click its button
        # The section title is "GL Non-Verbal Reasoning" and has a "Free sample test" button
        nvr_section = page.locator("text=GL Non-Verbal Reasoning").first
        if await nvr_section.count() > 0:
            # Click the "Free sample test" button in the NVR card (3rd card)
            buttons = page.locator("text=Free sample test")
            # NVR is the 3rd card (0=Maths, 1=English, 2=NVR, 3=VR)
            await buttons.nth(2).click()
        else:
            print("   Could not find NVR section, trying direct click...")
            await page.mouse.click(400, 189)  # Approximate button location from screenshot
        
        await page.wait_for_timeout(3000)
        
        print("3. Taking screenshot to verify Q1 loaded...")
        await page.screenshot(path=f"{OUTPUT_DIR}/q1_screenshot.png")
        
        print("4. Extracting base64 images...")
        images_data = await page.evaluate("""
            () => {
                const images = Array.from(document.querySelectorAll('img')).filter(img => img.src.startsWith('data:image'));
                return images.map((img, i) => ({
                    index: i,
                    src: img.src
                }));
            }
        """)
        
        print(f"   Found {len(images_data)} base64 images")
        
        # Save images
        if len(images_data) >= 5:
            labels = ['a', 'b', 'c', 'd', 'e']
            
            # For Q1, all 5 or 6 images could be options (no main for "odd one out")
            # Let's save based on count
            for i, img_data in enumerate(images_data[:6]):
                # Decode and save
                src = img_data['src']
                if src.startswith('data:image/png;base64,'):
                    b64 = src.split(',')[1]
                    
                    if i == 0 and len(images_data) >= 6:
                        filename = "nvr_q1_main.png"
                    else:
                        idx = i if len(images_data) == 5 else i - 1
                        if idx < 0:
                            filename = "nvr_q1_main.png"
                        else:
                            filename = f"nvr_q1_opt_{labels[idx]}.png" if idx < 5 else f"nvr_q1_extra_{i}.png"
                    
                    filepath = f"{OUTPUT_DIR}/{filename}"
                    with open(filepath, "wb") as f:
                        f.write(base64.b64decode(b64))
                    print(f"   Saved: {filename}")
        else:
            print("   ERROR: Not enough images found!")
        
        print("5. Done!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(extract_q1())
