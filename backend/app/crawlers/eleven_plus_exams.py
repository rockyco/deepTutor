"""Crawler for elevenplusexams.co.uk content.

Source: https://www.elevenplusexams.co.uk
Content: Free practice papers and resources for 11+ preparation
Focus: Verbal Reasoning papers
"""

import logging
import re
from urllib.parse import urljoin

from .base import BaseCrawler
from .models import RawQuestion
from .pdf_extractor import PDFExtractor

logger = logging.getLogger(__name__)


class ElevenPlusExamsCrawler(BaseCrawler):
    """Crawler for elevenplusexams.co.uk.

    Site provides free VR and other 11+ resources.
    """

    BASE_URL = "https://www.elevenplusexams.co.uk"
    SOURCE_NAME = "elevenplusexams.co.uk"
    REQUEST_DELAY = 2.5

    SUBJECT_PATHS = {
        "verbal_reasoning": "verbal-reasoning",
        "non_verbal_reasoning": "non-verbal-reasoning",
        "maths": "maths",
        "english": "english",
    }

    # VR category detection
    VR_CATEGORY_PATTERNS = {
        "synonym": "vr_synonyms",
        "antonym": "vr_synonyms",
        "odd one": "vr_odd_ones_out",
        "hidden word": "vr_hidden_word",
        "letter series": "vr_letter_series",
        "number series": "vr_number_series",
        "code": "vr_alphabet_code",
        "compound": "vr_compound_words",
        "anagram": "vr_anagrams",
        "word pair": "vr_word_pairs",
        "logic": "vr_logic_problems",
        "analogy": "vr_word_pairs",
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pdf_extractor = PDFExtractor()
        self._crawled_urls: set[str] = set()

    async def get_quiz_urls(self, subject: str) -> list[str]:
        """Get quiz/paper URLs for a subject."""
        if subject not in self.SUBJECT_PATHS:
            raise ValueError(f"Unknown subject: {subject}")

        urls = []
        path = self.SUBJECT_PATHS[subject]

        # Try common URL patterns for free resources
        search_urls = [
            f"{self.BASE_URL}/{path}/",
            f"{self.BASE_URL}/free-papers/{path}/",
            f"{self.BASE_URL}/practice-papers/{path}/",
            f"{self.BASE_URL}/resources/{path}/",
        ]

        for search_url in search_urls:
            html = await self.fetch(search_url)
            if html:
                found_urls = self._extract_resource_urls(html, search_url)
                for url in found_urls:
                    if url not in urls:
                        urls.append(url)

        logger.info(f"Found {len(urls)} resource URLs for {subject}")
        return urls

    def _extract_resource_urls(self, html: str, base_url: str) -> list[str]:
        """Extract resource URLs from HTML page."""
        soup = self.parse_html(html)
        urls = []

        for link in soup.find_all("a", href=True):
            href = link["href"]
            full_url = urljoin(base_url, href)

            # Look for PDFs
            if href.lower().endswith(".pdf"):
                if full_url not in urls:
                    urls.append(full_url)
                continue

            # Look for quiz/practice pages
            text = link.get_text(strip=True).lower()
            if any(w in text for w in ["quiz", "practice", "test", "paper", "worksheet"]):
                if full_url not in urls and full_url != base_url:
                    urls.append(full_url)

        return urls

    async def parse_quiz(self, url: str, html: str) -> list[RawQuestion]:
        """Parse questions from a quiz page or PDF."""
        if url in self._crawled_urls:
            return []
        self._crawled_urls.add(url)

        # Handle PDF
        if url.lower().endswith(".pdf"):
            return await self._parse_pdf(url)

        # Parse HTML quiz page
        return self._parse_html_quiz(html, url)

    async def _parse_pdf(self, url: str) -> list[RawQuestion]:
        """Extract questions from PDF."""
        category = self._detect_category(url)
        return await self.pdf_extractor.extract_questions_from_url(
            url,
            source_name=self.SOURCE_NAME,
            category=category,
        )

    def _parse_html_quiz(self, html: str, url: str) -> list[RawQuestion]:
        """Parse questions from HTML quiz page."""
        soup = self.parse_html(html)
        questions = []
        category = self._detect_category(url)

        # Try to find question containers
        # Pattern 1: Numbered list items
        questions.extend(self._parse_numbered_questions(soup, category))

        # Pattern 2: Question divs/sections
        if not questions:
            questions.extend(self._parse_question_sections(soup, category))

        # Pattern 3: Form-based quizzes
        if not questions:
            questions.extend(self._parse_form_quiz(soup, category))

        return questions

    def _parse_numbered_questions(
        self, soup, category: str
    ) -> list[RawQuestion]:
        """Parse questions in numbered list format."""
        questions = []

        # Find ordered lists that might contain questions
        for ol in soup.find_all(["ol", "ul"]):
            items = ol.find_all("li")
            if len(items) < 2:
                continue

            for item in items:
                text = item.get_text(strip=True)

                # Skip if too short
                if len(text) < 15:
                    continue

                # Look for options within the item
                options = self._extract_options(item)
                if len(options) >= 2:
                    # Clean question text
                    q_text = re.sub(r"^\d+[\.\)]\s*", "", text)
                    # Remove option text from question
                    for opt in options:
                        q_text = q_text.replace(opt, "").strip()

                    if len(q_text) >= 10:
                        questions.append(RawQuestion(
                            question_text=q_text,
                            options=options,
                            correct_answer=options[0],
                            source_category=category,
                        ))

        return questions

    def _parse_question_sections(
        self, soup, category: str
    ) -> list[RawQuestion]:
        """Parse questions from div/section containers."""
        questions = []

        # Find elements that look like questions
        question_elements = soup.find_all(
            ["div", "section", "article"],
            class_=re.compile(r"question|quiz-item|q-\d", re.I)
        )

        for elem in question_elements:
            # Get question text
            q_elem = elem.find(["h3", "h4", "p", "span"], class_=re.compile(r"question|text", re.I))
            if not q_elem:
                q_elem = elem.find(["h3", "h4"])
            if not q_elem:
                continue

            q_text = q_elem.get_text(strip=True)
            if len(q_text) < 10:
                continue

            # Get options
            options = self._extract_options(elem)
            if len(options) >= 2:
                questions.append(RawQuestion(
                    question_text=q_text,
                    options=options,
                    correct_answer=options[0],
                    source_category=category,
                ))

        return questions

    def _parse_form_quiz(self, soup, category: str) -> list[RawQuestion]:
        """Parse questions from form-based quizzes."""
        questions = []

        # Find radio button groups (common quiz format)
        form = soup.find("form")
        if not form:
            return questions

        # Group radio buttons by name
        radio_groups: dict[str, list] = {}
        for radio in form.find_all("input", {"type": "radio"}):
            name = radio.get("name", "")
            if name:
                if name not in radio_groups:
                    radio_groups[name] = []
                # Get label
                label = radio.find_next("label")
                if label:
                    radio_groups[name].append({
                        "value": radio.get("value", ""),
                        "text": label.get_text(strip=True),
                    })

        # For each group, try to find the question
        for name, radios in radio_groups.items():
            if len(radios) < 2:
                continue

            # Find question text - look for nearby label or heading
            q_text = ""
            # Try to find by question number in name
            match = re.search(r"q(\d+)", name, re.I)
            if match:
                q_num = match.group(1)
                q_elem = form.find(string=re.compile(rf"^\s*{q_num}[\.\)]\s*"))
                if q_elem:
                    q_text = q_elem.get_text(strip=True) if hasattr(q_elem, 'get_text') else str(q_elem)

            if q_text and len(q_text) >= 10:
                options = [r["text"] for r in radios if r["text"]]
                if len(options) >= 2:
                    questions.append(RawQuestion(
                        question_text=q_text,
                        options=options,
                        correct_answer=options[0],
                        source_category=category,
                    ))

        return questions

    def _extract_options(self, elem) -> list[str]:
        """Extract options from an element."""
        options = []

        # Look for labeled options (A), B), etc.)
        text = elem.get_text(separator="\n")
        option_pattern = re.compile(r"^\s*([A-Ea-e])\s*[\.\)\:]?\s*(.+)$", re.MULTILINE)

        for match in option_pattern.finditer(text):
            opt_text = match.group(2).strip()
            if opt_text and len(opt_text) < 200:
                options.append(opt_text)

        if options:
            return options[:5]

        # Try finding list items
        for li in elem.find_all("li")[:5]:
            text = li.get_text(strip=True)
            text = re.sub(r"^[A-Ea-e][\.\)\:]?\s*", "", text)
            if text and len(text) < 200:
                options.append(text)

        return options

    def _detect_category(self, url: str) -> str:
        """Detect category from URL."""
        url_lower = url.lower()

        for pattern, category in self.VR_CATEGORY_PATTERNS.items():
            if pattern in url_lower:
                return category

        return ""
