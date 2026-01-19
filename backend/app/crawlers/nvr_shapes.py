"""Crawler for Non-Verbal Reasoning shape-based questions.

Specialized crawler for NVR questions that involve visual shapes and patterns.
Handles image extraction and multi-image question types.

Question types:
- nvr_sequences: Shape pattern sequences
- nvr_odd_one_out: Find the different shape
- nvr_analogies: A is to B as C is to ?
- nvr_matrices: Grid pattern completion
- nvr_rotation: Shape rotation questions
- nvr_reflection: Mirror/reflection questions
- nvr_spatial_3d: 3D visualization (cube nets, folding)
"""

import hashlib
import logging
import re
from pathlib import Path
from urllib.parse import urljoin

from .base import BaseCrawler
from .models import RawQuestion
from .pdf_extractor import PDFExtractor

logger = logging.getLogger(__name__)


class NVRShapesCrawler(BaseCrawler):
    """Specialized crawler for NVR shape-based questions.

    Focuses on extracting visual questions with images.
    """

    BASE_URL = ""  # Multiple sources
    SOURCE_NAME = "nvr_shapes"
    REQUEST_DELAY = 3.0

    # NVR-focused sources
    NVR_SOURCES = [
        {
            "name": "sats-papers-nvr",
            "base_url": "https://www.sats-papers.co.uk",
            "paths": [
                "/11-plus-papers/non-verbal-reasoning/",
            ],
        },
        {
            "name": "examberry-nvr",
            "base_url": "https://www.examberrypapers.co.uk",
            "paths": [
                "/non-verbal-reasoning/",
                "/nvr/",
            ],
        },
    ]

    # NVR question type detection patterns
    NVR_TYPE_PATTERNS = {
        "sequence": "nvr_sequences",
        "series": "nvr_sequences",
        "pattern": "nvr_sequences",
        "complete the series": "nvr_sequences",
        "next in": "nvr_sequences",
        "odd one out": "nvr_odd_one_out",
        "odd one": "nvr_odd_one_out",
        "different from": "nvr_odd_one_out",
        "does not belong": "nvr_odd_one_out",
        "analogy": "nvr_analogies",
        "analogies": "nvr_analogies",
        "is to": "nvr_analogies",
        "relates to": "nvr_analogies",
        "matrix": "nvr_matrices",
        "matrices": "nvr_matrices",
        "grid": "nvr_matrices",
        "rotation": "nvr_rotation",
        "rotate": "nvr_rotation",
        "turn": "nvr_rotation",
        "clockwise": "nvr_rotation",
        "reflection": "nvr_reflection",
        "reflect": "nvr_reflection",
        "mirror": "nvr_reflection",
        "flip": "nvr_reflection",
        "3d": "nvr_spatial_3d",
        "cube": "nvr_spatial_3d",
        "net": "nvr_spatial_3d",
        "fold": "nvr_spatial_3d",
        "unfold": "nvr_spatial_3d",
        "spatial": "nvr_spatial_3d",
    }

    def __init__(
        self,
        images_dir: str = "backend/data/images/nvr",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.images_dir = Path(images_dir)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_extractor = PDFExtractor(images_dir=images_dir)
        self._crawled_urls: set[str] = set()

    async def get_quiz_urls(self, subject: str = "non_verbal_reasoning") -> list[str]:
        """Get NVR PDF and page URLs from multiple sources."""
        if subject != "non_verbal_reasoning":
            logger.warning(f"NVRShapesCrawler only supports non_verbal_reasoning, got {subject}")

        pdf_urls = []

        for source in self.NVR_SOURCES:
            base_url = source["base_url"]

            for path in source["paths"]:
                full_url = f"{base_url}{path}"
                try:
                    html = await self.fetch(full_url)
                    if html:
                        urls = self._extract_nvr_urls(html, full_url)
                        for url in urls:
                            if url not in pdf_urls:
                                pdf_urls.append(url)
                except Exception as e:
                    logger.warning(f"Error fetching {full_url}: {e}")

        logger.info(f"Found {len(pdf_urls)} NVR resource URLs")
        return pdf_urls

    def _extract_nvr_urls(self, html: str, base_url: str) -> list[str]:
        """Extract NVR-related URLs from HTML."""
        soup = self.parse_html(html)
        urls = []

        for link in soup.find_all("a", href=True):
            href = link["href"]
            full_url = urljoin(base_url, href)

            # Check if URL contains NVR indicators
            url_lower = full_url.lower()
            is_nvr = any(ind in url_lower for ind in [
                "nvr", "non-verbal", "nonverbal", "shape", "pattern",
                "sequence", "spatial", "visual"
            ])

            if not is_nvr:
                continue

            # Check for PDF
            if href.lower().endswith(".pdf"):
                if full_url not in urls:
                    urls.append(full_url)
                continue

            # Check for quiz/practice pages
            text = link.get_text(strip=True).lower()
            if any(w in text for w in ["practice", "test", "quiz", "paper", "worksheet"]):
                if full_url not in urls and full_url != base_url:
                    urls.append(full_url)

        return urls

    async def parse_quiz(self, url: str, html: str) -> list[RawQuestion]:
        """Parse NVR questions from URL."""
        if url in self._crawled_urls:
            return []
        self._crawled_urls.add(url)

        if url.lower().endswith(".pdf"):
            return await self._parse_nvr_pdf(url)

        # Parse HTML page for NVR questions
        return self._parse_nvr_html(html, url)

    async def _parse_nvr_pdf(self, url: str) -> list[RawQuestion]:
        """Extract NVR questions from PDF with image handling."""
        questions = await self.pdf_extractor.extract_questions_from_url(
            url,
            source_name=self.SOURCE_NAME,
            category=self._detect_nvr_type_from_url(url),
            extract_images=True,  # Always extract images for NVR
        )

        # Post-process to ensure proper NVR categorization
        for q in questions:
            if not q.source_category:
                q.source_category = self._detect_nvr_type(q.question_text)

        return questions

    def _parse_nvr_html(self, html: str, url: str) -> list[RawQuestion]:
        """Parse NVR questions from HTML page."""
        soup = self.parse_html(html)
        questions = []

        # Find question containers
        containers = soup.find_all(
            ["div", "section", "article"],
            class_=re.compile(r"question|quiz|nvr|visual", re.I)
        )

        for container in containers:
            try:
                q = self._parse_nvr_container(container, url)
                if q:
                    questions.append(q)
            except Exception as e:
                logger.debug(f"Failed to parse NVR container: {e}")

        # Also try numbered questions with images
        questions.extend(self._parse_numbered_nvr_questions(soup, url))

        return questions

    def _parse_nvr_container(self, container, url: str) -> RawQuestion | None:
        """Parse a single NVR question container."""
        # Get question text
        q_elem = container.find(["h3", "h4", "p"], class_=re.compile(r"question|text", re.I))
        if not q_elem:
            q_elem = container.find(["h3", "h4", "p"])
        if not q_elem:
            return None

        q_text = q_elem.get_text(strip=True)
        if len(q_text) < 5:
            return None

        # Extract images
        images = []
        for img in container.find_all("img"):
            src = img.get("src", "")
            if src:
                full_src = urljoin(url, src)
                images.append(full_src)

        # Get options
        options = []
        option_elements = container.find_all(
            ["div", "span", "li"],
            class_=re.compile(r"option|answer|choice", re.I)
        )
        if not option_elements:
            option_elements = container.find_all("li")

        for opt in option_elements[:5]:
            # Check for image option
            img = opt.find("img")
            if img:
                src = img.get("src", "")
                if src:
                    options.append(urljoin(url, src))
            else:
                text = opt.get_text(strip=True)
                text = re.sub(r"^[A-Ea-e][\.\)\:]?\s*", "", text)
                if text:
                    options.append(text)

        if len(options) < 2:
            return None

        # Detect question type
        category = self._detect_nvr_type(q_text)

        return RawQuestion(
            question_text=q_text,
            options=options,
            correct_answer=options[0],
            image_urls=images,
            source_category=category,
        )

    def _parse_numbered_nvr_questions(self, soup, url: str) -> list[RawQuestion]:
        """Parse numbered NVR questions."""
        questions = []

        # Find all potential question elements
        text = soup.get_text(separator="\n")
        question_pattern = re.compile(
            r"^\s*(?:Q(?:uestion)?\.?\s*)?(\d{1,2})\s*[\.\)\:]?\s*(.+?)$",
            re.MULTILINE | re.IGNORECASE
        )

        matches = list(question_pattern.finditer(text))

        for i, match in enumerate(matches):
            q_text = match.group(2).strip()

            # Only process if it looks like an NVR question
            if not self._looks_like_nvr_question(q_text):
                continue

            # Get question block
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            block = text[start:end]

            # Extract options
            options = []
            opt_pattern = re.compile(r"^\s*([A-Ea-e])\s*[\.\)\:]?\s*(.+)$", re.MULTILINE)
            for opt_match in opt_pattern.finditer(block):
                opt_text = opt_match.group(2).strip()
                if opt_text and len(opt_text) < 200:
                    options.append(opt_text)

            if len(options) >= 2:
                questions.append(RawQuestion(
                    question_text=q_text,
                    options=options[:5],
                    correct_answer=options[0],
                    source_category=self._detect_nvr_type(q_text),
                ))

        return questions

    def _looks_like_nvr_question(self, text: str) -> bool:
        """Check if text looks like an NVR question."""
        text_lower = text.lower()

        nvr_indicators = [
            "shape", "pattern", "sequence", "figure", "image",
            "diagram", "odd one", "which", "next", "complete",
            "rotate", "reflect", "mirror", "fold", "cube",
            "matrix", "grid", "analogy", "is to",
        ]

        return any(ind in text_lower for ind in nvr_indicators)

    def _detect_nvr_type(self, text: str) -> str:
        """Detect NVR question type from text."""
        text_lower = text.lower()

        for pattern, nvr_type in self.NVR_TYPE_PATTERNS.items():
            if pattern in text_lower:
                return nvr_type

        return "nvr_sequences"  # Default

    def _detect_nvr_type_from_url(self, url: str) -> str:
        """Detect NVR type from URL."""
        url_lower = url.lower()

        for pattern, nvr_type in self.NVR_TYPE_PATTERNS.items():
            pattern_url = pattern.replace(" ", "-")
            if pattern_url in url_lower:
                return nvr_type

        return ""

    async def crawl_all_nvr(self) -> dict:
        """Crawl all NVR sources and return combined results."""
        from datetime import datetime
        from .models import CrawlResult

        all_questions = []
        errors = []
        started_at = datetime.utcnow()

        # Crawl from all sources
        pdf_urls = await self.get_quiz_urls()

        for i, url in enumerate(pdf_urls, 1):
            logger.info(f"Processing NVR resource {i}/{len(pdf_urls)}: {url}")

            try:
                if url.lower().endswith(".pdf"):
                    questions = await self._parse_nvr_pdf(url)
                else:
                    html = await self.fetch(url)
                    if html:
                        questions = self._parse_nvr_html(html, url)
                    else:
                        questions = []

                for q in questions:
                    q.source_url = url
                    all_questions.append(q)

                logger.info(f"  Extracted {len(questions)} NVR questions")

            except Exception as e:
                error_msg = f"Error processing {url}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        result = CrawlResult(
            source=self.SOURCE_NAME,
            subject="non_verbal_reasoning",
            questions=all_questions,
            total_urls_found=len(pdf_urls),
            total_urls_crawled=len(pdf_urls) - len(errors),
            total_questions_extracted=len(all_questions),
            errors=errors,
            started_at=started_at,
            completed_at=datetime.utcnow(),
        )

        logger.info(result.summary())
        return result

    async def download_and_save_image(
        self, url: str, prefix: str = "nvr"
    ) -> str | None:
        """Download an image and save to images directory.

        Args:
            url: Image URL
            prefix: Filename prefix

        Returns:
            Relative path to saved image, or None on failure
        """
        import httpx

        try:
            headers = {"User-Agent": self.USER_AGENT}

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                # Determine extension
                content_type = response.headers.get("content-type", "")
                if "png" in content_type:
                    ext = ".png"
                elif "jpeg" in content_type or "jpg" in content_type:
                    ext = ".jpg"
                elif "gif" in content_type:
                    ext = ".gif"
                else:
                    ext = ".png"

                # Generate filename
                url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
                filename = f"{prefix}_{url_hash}{ext}"
                filepath = self.images_dir / filename

                filepath.write_bytes(response.content)
                logger.debug(f"Saved image: {filepath}")

                return f"images/nvr/{filename}"

        except Exception as e:
            logger.warning(f"Failed to download image {url}: {e}")
            return None
