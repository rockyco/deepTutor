"""PDF extraction utilities for crawled documents.

Handles downloading, text extraction, and question parsing from PDF files.
"""

import asyncio
import hashlib
import logging
import re
import tempfile
from pathlib import Path
from typing import Any

import httpx
import pdfplumber
from PIL import Image

from .models import RawQuestion

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract questions from PDF documents.

    Supports:
    - Downloading PDFs from URLs
    - Text extraction with layout preservation
    - Question pattern detection (numbered questions, A-D options)
    - Image extraction for NVR questions
    - Answer key parsing
    """

    USER_AGENT = (
        "Mozilla/5.0 (compatible; DeepTutorBot/1.0; "
        "+https://github.com/deeptutor; educational research)"
    )
    TIMEOUT = 60.0
    MAX_PDF_SIZE = 50 * 1024 * 1024  # 50MB limit

    # Question patterns
    QUESTION_PATTERN = re.compile(
        r"^\s*(?:Q(?:uestion)?\.?\s*)?(\d{1,3})\s*[\.\)\:]?\s*(.+?)$",
        re.MULTILINE | re.IGNORECASE
    )
    OPTION_PATTERN = re.compile(
        r"^\s*([A-Ea-e])\s*[\.\)\:]?\s*(.+)$"
    )
    ANSWER_KEY_PATTERN = re.compile(
        r"(?:Answer|Ans)[\s\.:]*(\d+)\s*[\.\)\:]?\s*([A-Ea-e])",
        re.IGNORECASE
    )

    def __init__(
        self,
        images_dir: Path | str = "backend/data/images/nvr",
        cache_dir: Path | str | None = None,
    ):
        """Initialize PDF extractor.

        Args:
            images_dir: Directory to save extracted images
            cache_dir: Directory to cache downloaded PDFs (uses temp if None)
        """
        self.images_dir = Path(images_dir)
        self.images_dir.mkdir(parents=True, exist_ok=True)

        self.cache_dir = Path(cache_dir) if cache_dir else None

    async def download_pdf(self, url: str) -> Path | None:
        """Download a PDF file from URL.

        Args:
            url: URL to download

        Returns:
            Path to downloaded file, or None on failure
        """
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "application/pdf,*/*",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.TIMEOUT,
                follow_redirects=True,
            ) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                # Check content type
                content_type = response.headers.get("content-type", "")
                if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
                    logger.warning(f"Not a PDF: {url} (content-type: {content_type})")
                    return None

                # Check size
                if len(response.content) > self.MAX_PDF_SIZE:
                    logger.warning(f"PDF too large: {url} ({len(response.content)} bytes)")
                    return None

                # Save to cache or temp
                url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
                filename = f"pdf_{url_hash}.pdf"

                if self.cache_dir:
                    self.cache_dir.mkdir(parents=True, exist_ok=True)
                    filepath = self.cache_dir / filename
                else:
                    filepath = Path(tempfile.gettempdir()) / filename

                filepath.write_bytes(response.content)
                logger.info(f"Downloaded PDF: {url} -> {filepath}")
                return filepath

        except httpx.TimeoutException:
            logger.error(f"Timeout downloading PDF: {url}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} downloading PDF: {url}")
        except Exception as e:
            logger.error(f"Error downloading PDF {url}: {e}")

        return None

    def extract_text(self, pdf_path: Path) -> str:
        """Extract text from PDF with layout preservation.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text content
        """
        text_parts = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"--- Page {page_num} ---\n{page_text}")
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")

        return "\n\n".join(text_parts)

    def extract_images(
        self, pdf_path: Path, prefix: str = "nvr"
    ) -> list[dict[str, Any]]:
        """Extract images from PDF.

        Args:
            pdf_path: Path to PDF file
            prefix: Prefix for saved image filenames

        Returns:
            List of dicts with image metadata (path, page, bbox)
        """
        images = []
        pdf_hash = hashlib.md5(pdf_path.read_bytes()).hexdigest()[:8]

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    for img_num, img in enumerate(page.images, 1):
                        try:
                            # Extract image bytes
                            x0, y0, x1, y1 = img["x0"], img["top"], img["x1"], img["bottom"]
                            cropped = page.within_bbox((x0, y0, x1, y1)).to_image()

                            # Save image
                            filename = f"{prefix}_{pdf_hash}_p{page_num}_i{img_num}.png"
                            filepath = self.images_dir / filename
                            cropped.save(str(filepath))

                            images.append({
                                "path": str(filepath),
                                "relative_path": f"images/nvr/{filename}",
                                "page": page_num,
                                "bbox": (x0, y0, x1, y1),
                            })
                            logger.debug(f"Extracted image: {filepath}")
                        except Exception as e:
                            logger.warning(f"Failed to extract image {img_num} from page {page_num}: {e}")
        except Exception as e:
            logger.error(f"Error extracting images from {pdf_path}: {e}")

        return images

    def parse_questions(
        self,
        text: str,
        source_url: str = "",
        source_name: str = "",
        category: str = "",
    ) -> list[RawQuestion]:
        """Parse questions from extracted text.

        Args:
            text: Extracted PDF text
            source_url: Source URL for attribution
            source_name: Source name
            category: Default category for questions

        Returns:
            List of parsed RawQuestion objects
        """
        questions = []

        # Try to find answer key first
        answers = self._extract_answer_key(text)

        # Find all question starts
        question_matches = list(self.QUESTION_PATTERN.finditer(text))

        for i, match in enumerate(question_matches):
            q_num = int(match.group(1))

            # Get text until next question or end
            start = match.start()
            if i + 1 < len(question_matches):
                end = question_matches[i + 1].start()
            else:
                end = len(text)

            question_block = text[start:end]

            # Parse the question block
            question = self._parse_question_block(
                question_block, q_num, answers.get(q_num)
            )
            if question:
                question.source_url = source_url
                question.source_name = source_name
                question.source_category = category
                questions.append(question)

        logger.info(f"Parsed {len(questions)} questions from PDF text")
        return questions

    def _extract_answer_key(self, text: str) -> dict[int, str]:
        """Extract answer key from text if present.

        Returns dict mapping question number to correct answer letter.
        """
        answers = {}

        # Look for answer key section
        answer_section = None
        for marker in ["Answer Key", "Answers", "Answer Sheet", "Solutions"]:
            idx = text.lower().find(marker.lower())
            if idx != -1:
                answer_section = text[idx:]
                break

        if answer_section:
            for match in self.ANSWER_KEY_PATTERN.finditer(answer_section):
                q_num = int(match.group(1))
                answer = match.group(2).upper()
                answers[q_num] = answer

        # Also try inline pattern: "1. A  2. B  3. C"
        inline_pattern = re.compile(r"(\d+)\s*[\.\)]\s*([A-Ea-e])(?:\s|$)")
        for match in inline_pattern.finditer(text):
            q_num = int(match.group(1))
            if q_num not in answers:  # Don't override answer key section
                answers[q_num] = match.group(2).upper()

        return answers

    def _parse_question_block(
        self,
        block: str,
        q_num: int,
        correct_answer: str | None,
    ) -> RawQuestion | None:
        """Parse a single question block.

        Args:
            block: Text block containing question and options
            q_num: Question number
            correct_answer: Known correct answer letter (A-E) if available

        Returns:
            RawQuestion or None if parsing fails
        """
        lines = [l.strip() for l in block.split("\n") if l.strip()]

        if len(lines) < 2:
            return None

        # First line is question (already matched, so extract just the text)
        question_text = re.sub(
            r"^\s*(?:Q(?:uestion)?\.?\s*)?\d{1,3}\s*[\.\)\:]?\s*",
            "",
            lines[0]
        )

        # Collect remaining text that's not an option as part of question
        remaining_question = []
        options = []
        option_letters = []

        for line in lines[1:]:
            opt_match = self.OPTION_PATTERN.match(line)
            if opt_match:
                letter = opt_match.group(1).upper()
                option_text = opt_match.group(2).strip()
                if option_text:
                    options.append(option_text)
                    option_letters.append(letter)
            elif not options:
                # Still part of question text
                remaining_question.append(line)

        # Combine question text
        if remaining_question:
            question_text = question_text + " " + " ".join(remaining_question)
        question_text = question_text.strip()

        # Need at least 2 options
        if len(options) < 2:
            return None

        # Determine correct answer
        correct = ""
        if correct_answer and correct_answer in option_letters:
            idx = option_letters.index(correct_answer)
            if idx < len(options):
                correct = options[idx]
        elif options:
            correct = options[0]  # Default to first option

        return RawQuestion(
            question_text=question_text,
            options=options[:5],  # Max 5 options (A-E)
            correct_answer=correct,
            explanation="",
        )

    async def extract_questions_from_url(
        self,
        url: str,
        source_name: str = "",
        category: str = "",
        extract_images: bool = False,
    ) -> list[RawQuestion]:
        """Full pipeline: download PDF and extract questions.

        Args:
            url: PDF URL to process
            source_name: Source attribution name
            category: Question category
            extract_images: Whether to extract images

        Returns:
            List of extracted questions
        """
        # Download
        pdf_path = await self.download_pdf(url)
        if not pdf_path:
            return []

        try:
            # Extract text
            text = self.extract_text(pdf_path)
            if not text:
                logger.warning(f"No text extracted from {url}")
                return []

            # Extract images if requested
            images = []
            if extract_images:
                images = self.extract_images(pdf_path)

            # Parse questions
            questions = self.parse_questions(
                text,
                source_url=url,
                source_name=source_name,
                category=category,
            )

            # Attach images to questions if present
            if images and questions:
                self._attach_images_to_questions(questions, images)

            return questions

        finally:
            # Clean up temp file if not caching
            if not self.cache_dir and pdf_path.exists():
                try:
                    pdf_path.unlink()
                except Exception:
                    pass

    def _attach_images_to_questions(
        self,
        questions: list[RawQuestion],
        images: list[dict[str, Any]],
    ) -> None:
        """Attach extracted images to questions based on page proximity.

        Simple heuristic: distribute images evenly among questions.
        """
        if not images or not questions:
            return

        # Group images by page
        images_per_page: dict[int, list] = {}
        for img in images:
            page = img.get("page", 1)
            if page not in images_per_page:
                images_per_page[page] = []
            images_per_page[page].append(img)

        # Simple distribution: if similar number of images and questions,
        # assign one image per question
        if len(images) == len(questions):
            for i, q in enumerate(questions):
                q.image_urls = [images[i]["relative_path"]]
        elif len(images) > len(questions):
            # Multiple images per question (e.g., sequences)
            imgs_per_q = len(images) // len(questions)
            for i, q in enumerate(questions):
                start = i * imgs_per_q
                end = start + imgs_per_q
                q.image_urls = [img["relative_path"] for img in images[start:end]]


class PDFQuestionParser:
    """Alternative parser for different PDF formats.

    Handles various 11+ paper formats from different publishers.
    """

    # GL Assessment format patterns
    GL_QUESTION_PATTERN = re.compile(
        r"^\s*(\d{1,2})\s+(.+?)(?:\s+[_\s]+)?$",
        re.MULTILINE
    )

    # CEM format patterns
    CEM_QUESTION_PATTERN = re.compile(
        r"^\s*Question\s+(\d+)\s*[:\.]?\s*(.+?)$",
        re.MULTILINE | re.IGNORECASE
    )

    @staticmethod
    def detect_format(text: str) -> str:
        """Detect the PDF format/publisher.

        Returns:
            Format identifier: 'gl', 'cem', 'bond', 'cgp', 'generic'
        """
        text_lower = text.lower()

        if "gl assessment" in text_lower or "gl education" in text_lower:
            return "gl"
        elif "cem" in text_lower or "durham university" in text_lower:
            return "cem"
        elif "bond" in text_lower and "nelson" in text_lower:
            return "bond"
        elif "cgp" in text_lower:
            return "cgp"

        return "generic"

    def parse_gl_format(self, text: str) -> list[RawQuestion]:
        """Parse GL Assessment format papers."""
        # GL papers often have compact question numbering
        questions = []
        # Implementation depends on specific GL paper layout
        return questions

    def parse_cem_format(self, text: str) -> list[RawQuestion]:
        """Parse CEM format papers."""
        questions = []
        # CEM papers have different section structure
        return questions
