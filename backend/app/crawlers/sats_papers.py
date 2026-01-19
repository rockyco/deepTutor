"""Crawler for sats-papers.co.uk 11+ content.

Source: https://www.sats-papers.co.uk/11-plus-papers/
Content: PDF papers with answers for VR, Maths, English, NVR
"""

import logging
import re
from urllib.parse import urljoin

from .base import BaseCrawler
from .models import RawQuestion
from .pdf_extractor import PDFExtractor

logger = logging.getLogger(__name__)


class SATSPapersCrawler(BaseCrawler):
    """Crawler for sats-papers.co.uk 11+ papers.

    Site structure:
    - Main listing: /11-plus-papers/
    - Subject pages with PDF download links
    - Papers available in PDF format with separate answer sheets
    """

    BASE_URL = "https://www.sats-papers.co.uk"
    SOURCE_NAME = "sats-papers.co.uk"
    REQUEST_DELAY = 3.0  # Be polite - educational site

    # Subject path mappings
    SUBJECT_PATHS = {
        "verbal_reasoning": "11-plus-papers/verbal-reasoning",
        "non_verbal_reasoning": "11-plus-papers/non-verbal-reasoning",
        "maths": "11-plus-papers/maths",
        "english": "11-plus-papers/english",
    }

    # Category detection patterns
    CATEGORY_PATTERNS = {
        # Verbal Reasoning
        "synonym": "vr_synonyms",
        "antonym": "vr_synonyms",
        "odd one out": "vr_odd_ones_out",
        "hidden word": "vr_hidden_word",
        "letter series": "vr_letter_series",
        "number series": "vr_number_series",
        "code": "vr_alphabet_code",
        "word pair": "vr_word_pairs",
        "anagram": "vr_anagrams",
        "compound": "vr_compound_words",
        # Non-Verbal Reasoning
        "sequence": "nvr_sequences",
        "pattern": "nvr_sequences",
        "analogy": "nvr_analogies",
        "matrix": "nvr_matrices",
        "reflection": "nvr_reflection",
        "rotation": "nvr_rotation",
        "3d": "nvr_spatial_3d",
        "cube": "nvr_spatial_3d",
        # Maths
        "fraction": "fractions",
        "decimal": "decimals",
        "percent": "percentages",
        "geometry": "geometry",
        "shape": "geometry",
        "algebra": "algebra",
        "ratio": "ratio",
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
        """Get list of PDF URLs for a subject.

        Returns URLs of PDF papers to download and extract.
        """
        if subject not in self.SUBJECT_PATHS:
            raise ValueError(f"Unknown subject: {subject}")

        path = self.SUBJECT_PATHS[subject]
        listing_url = f"{self.BASE_URL}/{path}/"

        logger.info(f"Fetching paper listing from {listing_url}")
        html = await self.fetch(listing_url)
        if not html:
            return []

        soup = self.parse_html(html)
        pdf_urls = []

        # Find PDF download links
        for link in soup.find_all("a", href=True):
            href = link["href"]

            # Skip if not a PDF
            if not href.lower().endswith(".pdf"):
                continue

            # Skip answer sheets for now (we'll pair them later)
            if "answer" in href.lower() and "question" not in href.lower():
                continue

            full_url = urljoin(self.BASE_URL, href)
            if full_url not in pdf_urls:
                pdf_urls.append(full_url)

        # Also look for links to paper pages that might have PDFs
        paper_pages = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "/11-plus" in href and href != f"/{path}/":
                page_url = urljoin(self.BASE_URL, href)
                if page_url not in paper_pages and page_url != listing_url:
                    paper_pages.append(page_url)

        # Crawl linked pages for more PDFs
        for page_url in paper_pages[:20]:  # Limit to avoid over-crawling
            try:
                page_html = await self.fetch(page_url)
                if page_html:
                    page_soup = self.parse_html(page_html)
                    for link in page_soup.find_all("a", href=True):
                        href = link["href"]
                        if href.lower().endswith(".pdf"):
                            full_url = urljoin(self.BASE_URL, href)
                            if full_url not in pdf_urls:
                                pdf_urls.append(full_url)
            except Exception as e:
                logger.warning(f"Error crawling {page_url}: {e}")

        logger.info(f"Found {len(pdf_urls)} PDF URLs for {subject}")
        return pdf_urls

    async def parse_quiz(self, url: str, html: str) -> list[RawQuestion]:
        """Extract questions from a PDF URL.

        Note: For PDF sources, the 'html' parameter is actually the PDF URL.
        We override the crawl method behavior for PDF handling.
        """
        # For PDF crawlers, we get PDF URL directly
        if not url.lower().endswith(".pdf"):
            # If it's an HTML page, look for PDF links
            return await self._extract_from_html_page(url, html)

        return await self._extract_from_pdf(url)

    async def _extract_from_pdf(self, pdf_url: str) -> list[RawQuestion]:
        """Extract questions from a PDF file."""
        if pdf_url in self._crawled_pdfs:
            logger.debug(f"Skipping already crawled PDF: {pdf_url}")
            return []

        self._crawled_pdfs.add(pdf_url)

        # Detect category from URL
        category = self._detect_category(pdf_url)

        # Check for associated answer sheet
        answer_url = self._find_answer_sheet_url(pdf_url)

        # Extract questions
        questions = await self.pdf_extractor.extract_questions_from_url(
            pdf_url,
            source_name=self.SOURCE_NAME,
            category=category,
            extract_images="nvr" in pdf_url.lower() or "non-verbal" in pdf_url.lower(),
        )

        # If we found an answer sheet, try to update correct answers
        if answer_url and questions:
            await self._apply_answer_sheet(questions, answer_url)

        return questions

    async def _extract_from_html_page(
        self, url: str, html: str
    ) -> list[RawQuestion]:
        """Extract questions from an HTML page containing PDFs."""
        soup = self.parse_html(html)
        questions = []

        # Find all PDF links on the page
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.lower().endswith(".pdf") and "answer" not in href.lower():
                pdf_url = urljoin(url, href)
                pdf_questions = await self._extract_from_pdf(pdf_url)
                questions.extend(pdf_questions)

        return questions

    def _detect_category(self, url: str) -> str:
        """Detect question category from URL."""
        url_lower = url.lower()

        for pattern, category in self.CATEGORY_PATTERNS.items():
            if pattern in url_lower:
                return category

        return ""

    def _find_answer_sheet_url(self, paper_url: str) -> str | None:
        """Find the answer sheet URL for a paper.

        Common patterns:
        - paper-1.pdf -> paper-1-answers.pdf
        - questions.pdf -> answers.pdf
        """
        # Try common answer sheet naming patterns
        patterns = [
            (r"\.pdf$", "-answers.pdf"),
            (r"\.pdf$", "_answers.pdf"),
            (r"-questions\.pdf$", "-answers.pdf"),
            (r"_questions\.pdf$", "_answers.pdf"),
            (r"paper(\d+)\.pdf$", r"answers\1.pdf"),
        ]

        for pattern, replacement in patterns:
            answer_url = re.sub(pattern, replacement, paper_url, flags=re.IGNORECASE)
            if answer_url != paper_url:
                return answer_url

        return None

    async def _apply_answer_sheet(
        self, questions: list[RawQuestion], answer_url: str
    ) -> None:
        """Apply answers from an answer sheet to questions."""
        try:
            pdf_path = await self.pdf_extractor.download_pdf(answer_url)
            if not pdf_path:
                return

            text = self.pdf_extractor.extract_text(pdf_path)
            if not text:
                return

            # Parse answer key
            answers = self.pdf_extractor._extract_answer_key(text)

            # Apply to questions
            for i, q in enumerate(questions, 1):
                if i in answers:
                    answer_letter = answers[i]
                    # Convert letter to option index
                    idx = ord(answer_letter.upper()) - ord('A')
                    if 0 <= idx < len(q.options):
                        q.correct_answer = q.options[idx]
                        logger.debug(f"Q{i}: Set answer to {answer_letter} ({q.options[idx]})")

        except Exception as e:
            logger.warning(f"Failed to apply answer sheet {answer_url}: {e}")

    async def crawl(self, subject: str):
        """Override crawl to handle PDF-based sources."""
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
                    questions = await self._extract_from_pdf(pdf_url)
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
