"""Crawler for examberrypapers.co.uk content.

Source: https://www.examberrypapers.co.uk
Content: PDF papers for all subjects, no sign-up required
"""

import logging
import re
from urllib.parse import urljoin

from .base import BaseCrawler
from .models import RawQuestion
from .pdf_extractor import PDFExtractor

logger = logging.getLogger(__name__)


class ExamBerryCrawler(BaseCrawler):
    """Crawler for examberrypapers.co.uk.

    Site provides free 11+ papers in PDF format across all subjects.
    """

    BASE_URL = "https://www.examberrypapers.co.uk"
    SOURCE_NAME = "examberrypapers.co.uk"
    REQUEST_DELAY = 2.5

    SUBJECT_PATHS = {
        "verbal_reasoning": ["verbal-reasoning", "vr"],
        "non_verbal_reasoning": ["non-verbal-reasoning", "nvr"],
        "maths": ["maths", "mathematics", "math"],
        "english": ["english", "comprehension", "grammar"],
    }

    # Category patterns for classification
    CATEGORY_PATTERNS = {
        # VR
        "synonym": "vr_synonyms",
        "antonym": "vr_synonyms",
        "odd one out": "vr_odd_ones_out",
        "hidden word": "vr_hidden_word",
        "letter series": "vr_letter_series",
        "number series": "vr_number_series",
        "code": "vr_alphabet_code",
        "compound word": "vr_compound_words",
        "anagram": "vr_anagrams",
        # NVR
        "sequence": "nvr_sequences",
        "pattern": "nvr_sequences",
        "analogy": "nvr_analogies",
        "matrix": "nvr_matrices",
        "reflection": "nvr_reflection",
        "rotation": "nvr_rotation",
        "cube": "nvr_spatial_3d",
        "fold": "nvr_spatial_3d",
        # Maths
        "fraction": "fractions",
        "decimal": "decimals",
        "percent": "percentages",
        "geometry": "geometry",
        "algebra": "algebra",
        "ratio": "ratio",
        "word problem": "word_problems",
        # English
        "comprehension": "comprehension",
        "grammar": "grammar",
        "spelling": "spelling",
        "vocabulary": "vocabulary",
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pdf_extractor = PDFExtractor()
        self._crawled_pdfs: set[str] = set()

    async def get_quiz_urls(self, subject: str) -> list[str]:
        """Get PDF URLs for a subject."""
        if subject not in self.SUBJECT_PATHS:
            raise ValueError(f"Unknown subject: {subject}")

        pdf_urls = []
        paths = self.SUBJECT_PATHS[subject]

        # Try different URL patterns
        for path in paths:
            search_urls = [
                f"{self.BASE_URL}/{path}/",
                f"{self.BASE_URL}/papers/{path}/",
                f"{self.BASE_URL}/11-plus/{path}/",
                f"{self.BASE_URL}/free-papers/{path}/",
            ]

            for search_url in search_urls:
                try:
                    html = await self.fetch(search_url)
                    if html:
                        urls = self._find_pdf_urls(html, search_url)
                        for url in urls:
                            if url not in pdf_urls:
                                pdf_urls.append(url)
                except Exception as e:
                    logger.debug(f"Error fetching {search_url}: {e}")

        # Also try main papers page
        main_url = f"{self.BASE_URL}/papers/"
        try:
            html = await self.fetch(main_url)
            if html:
                # Filter by subject keywords
                urls = self._find_pdf_urls(html, main_url)
                for url in urls:
                    if any(p in url.lower() for p in paths):
                        if url not in pdf_urls:
                            pdf_urls.append(url)
        except Exception as e:
            logger.debug(f"Error fetching main papers page: {e}")

        logger.info(f"Found {len(pdf_urls)} PDF URLs for {subject}")
        return pdf_urls

    def _find_pdf_urls(self, html: str, base_url: str) -> list[str]:
        """Find PDF URLs in HTML."""
        soup = self.parse_html(html)
        urls = []

        for link in soup.find_all("a", href=True):
            href = link["href"]

            if not href.lower().endswith(".pdf"):
                continue

            # Skip answer sheets for initial crawl
            if "answer" in href.lower() and "question" not in href.lower():
                continue

            full_url = urljoin(base_url, href)
            if full_url not in urls:
                urls.append(full_url)

        return urls

    async def parse_quiz(self, url: str, html: str) -> list[RawQuestion]:
        """Parse questions from a PDF or page."""
        if url.lower().endswith(".pdf"):
            return await self._parse_pdf(url)

        # For HTML pages, find PDFs and parse them
        soup = self.parse_html(html)
        questions = []

        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.lower().endswith(".pdf"):
                pdf_url = urljoin(url, href)
                pdf_questions = await self._parse_pdf(pdf_url)
                questions.extend(pdf_questions)

        return questions

    async def _parse_pdf(self, url: str) -> list[RawQuestion]:
        """Parse questions from a PDF file."""
        if url in self._crawled_pdfs:
            return []
        self._crawled_pdfs.add(url)

        category = self._detect_category(url)
        is_nvr = "nvr" in url.lower() or "non-verbal" in url.lower()

        questions = await self.pdf_extractor.extract_questions_from_url(
            url,
            source_name=self.SOURCE_NAME,
            category=category,
            extract_images=is_nvr,
        )

        # Try to find and apply answer sheet
        answer_url = self._find_answer_url(url)
        if answer_url:
            await self._apply_answers(questions, answer_url)

        return questions

    def _detect_category(self, url: str) -> str:
        """Detect category from URL."""
        url_lower = url.lower()

        for pattern, category in self.CATEGORY_PATTERNS.items():
            if pattern.replace(" ", "-") in url_lower or pattern.replace(" ", "_") in url_lower:
                return category

        return ""

    def _find_answer_url(self, paper_url: str) -> str | None:
        """Find corresponding answer sheet URL."""
        patterns = [
            (r"questions?\.pdf$", "answers.pdf"),
            (r"paper\.pdf$", "answers.pdf"),
            (r"\.pdf$", "-answers.pdf"),
            (r"\.pdf$", "_answers.pdf"),
        ]

        for pattern, replacement in patterns:
            answer_url = re.sub(pattern, replacement, paper_url, flags=re.IGNORECASE)
            if answer_url != paper_url:
                return answer_url

        return None

    async def _apply_answers(
        self, questions: list[RawQuestion], answer_url: str
    ) -> None:
        """Apply answers from answer sheet."""
        try:
            pdf_path = await self.pdf_extractor.download_pdf(answer_url)
            if not pdf_path:
                return

            text = self.pdf_extractor.extract_text(pdf_path)
            answers = self.pdf_extractor._extract_answer_key(text)

            for i, q in enumerate(questions, 1):
                if i in answers:
                    letter = answers[i]
                    idx = ord(letter.upper()) - ord('A')
                    if 0 <= idx < len(q.options):
                        q.correct_answer = q.options[idx]

        except Exception as e:
            logger.warning(f"Failed to apply answers from {answer_url}: {e}")

    async def crawl(self, subject: str):
        """Override crawl for PDF-based source."""
        from datetime import datetime
        from .models import CrawlResult

        result = CrawlResult(
            source=self.SOURCE_NAME,
            subject=subject,
            questions=[],
            started_at=datetime.utcnow(),
        )

        try:
            pdf_urls = await self.get_quiz_urls(subject)
            result.total_urls_found = len(pdf_urls)

            for i, pdf_url in enumerate(pdf_urls, 1):
                logger.info(f"Processing PDF {i}/{len(pdf_urls)}: {pdf_url}")

                try:
                    questions = await self._parse_pdf(pdf_url)
                    result.total_urls_crawled += 1

                    for q in questions:
                        q.source_url = pdf_url
                        q.source_name = self.SOURCE_NAME
                        result.questions.append(q)

                    logger.info(f"  Extracted {len(questions)} questions")

                except Exception as e:
                    error_msg = f"Error processing {pdf_url}: {e}"
                    logger.error(error_msg)
                    result.errors.append(error_msg)

        except Exception as e:
            error_msg = f"Failed to get PDF URLs: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)

        result.total_questions_extracted = len(result.questions)
        result.completed_at = datetime.utcnow()

        logger.info(result.summary())
        return result
