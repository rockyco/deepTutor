"""Script to download GL Assessment familiarisation materials."""

import asyncio
import sys
from pathlib import Path
import zipfile
import io

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

from app.config import settings

# GL Assessment free materials URLs
MATERIAL_URLS = {
    "verbal-reasoning": "https://cdn.shopify.com/s/files/1/0681/5498/2630/files/verbal-reasoning.zip",
    "non-verbal-reasoning": "https://cdn.shopify.com/s/files/1/0681/5498/2630/files/non-verbal-reasoning.zip",
    "english": "https://cdn.shopify.com/s/files/1/0681/5498/2630/files/english_1.zip",
    "maths": "https://cdn.shopify.com/s/files/1/0681/5498/2630/files/maths.zip",
    "verbal-skills": "https://cdn.shopify.com/s/files/1/0681/5498/2630/files/verbal-skills.zip",
}


async def download_and_extract(
    client: httpx.AsyncClient,
    name: str,
    url: str,
    output_dir: Path,
) -> bool:
    """Download a zip file and extract it."""
    try:
        print(f"Downloading {name}...")
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()

        # Create output directory
        material_dir = output_dir / name
        material_dir.mkdir(parents=True, exist_ok=True)

        # Extract zip
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            zf.extractall(material_dir)

        print(f"  Extracted to {material_dir}")
        return True

    except Exception as e:
        print(f"  Failed to download {name}: {e}")
        return False


async def main():
    """Download all GL Assessment materials."""
    print("Downloading GL Assessment familiarisation materials...")
    print(f"Output directory: {settings.materials_dir}")
    print()

    settings.materials_dir.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=60.0) as client:
        tasks = [
            download_and_extract(client, name, url, settings.materials_dir)
            for name, url in MATERIAL_URLS.items()
        ]
        results = await asyncio.gather(*tasks)

    successful = sum(results)
    print()
    print(f"Downloaded {successful}/{len(MATERIAL_URLS)} materials successfully.")

    # List downloaded files
    print()
    print("Downloaded materials:")
    for path in settings.materials_dir.rglob("*"):
        if path.is_file():
            rel_path = path.relative_to(settings.materials_dir)
            print(f"  {rel_path}")


if __name__ == "__main__":
    asyncio.run(main())
