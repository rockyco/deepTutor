"""Playwright-based crawler for educationquizzes.com 11+ content.

This crawler uses Playwright to render JavaScript-heavy pages and extract
quiz questions from the fully rendered DOM.
"""

import asyncio
import logging
import re
from urllib.parse import urljoin

from playwright.async_api import async_playwright, Page, Browser

from .models import RawQuestion, CrawlResult
from datetime import datetime

logger = logging.getLogger(__name__)


class EducationQuizzesPlaywrightCrawler:
    """Playwright-based crawler for educationquizzes.com.

    Uses headless browser to render JavaScript and extract quiz content.
    """

    BASE_URL = "https://www.educationquizzes.com"
    SOURCE_NAME = "educationquizzes.com"
    REQUEST_DELAY = 2.0  # seconds between requests

    # Map our subject names to their URL paths
    SUBJECT_PATHS = {
        "verbal_reasoning": "11-plus/verbal-reasoning",
        "non_verbal_reasoning": "11-plus/non-verbal-reasoning",
        "maths": "11-plus/maths",
        "english": "11-plus/english",
    }

    # Category patterns for question type classification
    CATEGORY_PATTERNS = {
        "synonyms": "vr_synonyms",
        "closest meaning": "vr_synonyms",
        "anagram": "vr_anagrams",
        "hidden word": "vr_hidden_word",
        "odd one": "vr_odd_ones_out",
        "insert a letter": "vr_insert_letter",
        "complete the word": "vr_insert_letter",
        "letter series": "vr_letter_series",
        "letter connections": "vr_letter_relationships",
        "number series": "vr_number_series",
        "number connections": "vr_number_connections",
        "complete the sum": "vr_number_connections",
        "compound words": "vr_compound_words",
        "codes": "vr_alphabet_code",
        "word connections": "vr_word_pairs",
        "logic": "vr_logic_problems",
        "sequences": "nvr_sequences",
        "analogies": "nvr_analogies",
        "matrices": "nvr_matrices",
        "reflection": "nvr_reflection",
        "rotation": "nvr_rotation",
        "spatial": "nvr_spatial_3d",
        "addition": "number_operations",
        "subtraction": "number_operations",
        "multiplication": "number_operations",
        "division": "number_operations",
        "fractions": "fractions",
        "decimals": "decimals",
        "percentages": "percentages",
        "geometry": "geometry",
        "shapes": "geometry",
        "measurement": "measurement",
        "data": "data_handling",
        "algebra": "algebra",
        "ratio": "ratio",
        "comprehension": "comprehension",
        "grammar": "grammar",
        "spelling": "spelling",
        "vocabulary": "vocabulary",
    }

    def __init__(self, request_delay: float | None = None, headless: bool = True):
        """Initialize crawler.

        Args:
            request_delay: Delay between requests in seconds
            headless: Run browser in headless mode
        """
        self.request_delay = request_delay or self.REQUEST_DELAY
        self.headless = headless
        self._browser: Browser | None = None
        self._playwright = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def _rate_limit(self) -> None:
        """Apply rate limiting delay."""
        await asyncio.sleep(self.request_delay)

    async def get_quiz_urls(self, subject: str) -> list[str]:
        """Get all quiz URLs for a subject from the listing page."""
        if subject not in self.SUBJECT_PATHS:
            raise ValueError(f"Unknown subject: {subject}")

        path = self.SUBJECT_PATHS[subject]
        listing_url = f"{self.BASE_URL}/{path}/"

        logger.info(f"Fetching quiz listing from {listing_url}")

        page = await self._browser.new_page()
        try:
            await page.goto(listing_url, wait_until="networkidle")
            await page.wait_for_timeout(1000)  # Extra wait for JS

            # Find all quiz links
            links = await page.query_selector_all(f'a[href*="/{path}/"]')
            quiz_urls = []

            for link in links:
                href = await link.get_attribute("href")
                if href and href != f"/{path}/" and href != f"/{path}":
                    full_url = urljoin(self.BASE_URL, href)
                    if full_url not in quiz_urls and "/verbal-reasoning/" not in full_url or path in full_url:
                        # Ensure it's a quiz page, not the listing
                        if re.search(rf"/{path}/[a-z0-9-]+/?$", full_url, re.I):
                            quiz_urls.append(full_url)

            logger.info(f"Found {len(quiz_urls)} quiz URLs for {subject}")
            return list(set(quiz_urls))  # Remove duplicates

        finally:
            await page.close()

    async def parse_quiz(self, page: Page, url: str) -> list[RawQuestion]:
        """Extract questions from a quiz page using Playwright.

        Args:
            page: Playwright page object
            url: The quiz URL

        Returns:
            List of extracted RawQuestion objects
        """
        questions = []
        category = self._extract_category_from_url(url)

        try:
            # Wait for quiz content to load
            await page.wait_for_selector("h1", timeout=10000)
            await page.wait_for_timeout(500)  # Extra wait for dynamic content

            # Find all question blocks - they have numbered format "1 .", "2 .", etc.
            # Based on the page structure, questions are in clickable generic divs
            question_elements = await page.query_selector_all('[class*="quiz"] > div > div')

            if not question_elements:
                # Try alternative selector
                question_elements = await page.query_selector_all('div:has(> div:text-matches("^\\d+\\s*\\.$"))')

            # Parse questions by looking for numbered patterns in the page
            content = await page.content()

            # Extract questions using regex on rendered HTML
            questions = await self._extract_questions_from_page(page, category)

        except Exception as e:
            logger.warning(f"Error parsing quiz {url}: {e}")

        return questions

    async def _extract_questions_from_page(
        self, page: Page, category: str
    ) -> list[RawQuestion]:
        """Extract questions from the rendered page."""
        questions = []

        # Get all text content to find numbered questions
        try:
            # Look for question containers with numbered format
            # The structure is: div containing "1 ." followed by question content

            # Find all elements that look like question numbers
            number_elements = await page.query_selector_all('div:text-matches("^\\d+\\s*\\.$")')

            for num_elem in number_elements:
                try:
                    # Get the parent container which has the full question
                    parent = await num_elem.evaluate_handle("el => el.parentElement")
                    if not parent:
                        continue

                    parent_elem = parent.as_element()
                    if not parent_elem:
                        continue

                    # Get question number
                    num_text = await num_elem.inner_text()
                    q_num = int(re.search(r"(\d+)", num_text).group(1))

                    # Get all text from the question container
                    full_text = await parent_elem.inner_text()

                    # Parse the question block
                    q = self._parse_question_text(full_text, q_num, category)
                    if q:
                        questions.append(q)

                except Exception as e:
                    logger.debug(f"Error parsing question element: {e}")
                    continue

            # If no questions found with the above method, try alternative approach
            if not questions:
                questions = await self._extract_questions_alternative(page, category)

        except Exception as e:
            logger.warning(f"Error extracting questions: {e}")

        return questions

    async def _extract_questions_alternative(
        self, page: Page, category: str
    ) -> list[RawQuestion]:
        """Alternative extraction method using page text content."""
        questions = []

        try:
            # Get the main content area text
            body_text = await page.inner_text("body")

            # Find numbered questions pattern
            # Pattern: digit(s) followed by period and space, then text until next question
            pattern = r"(\d{1,2})\s*\.\s*\n(.*?)(?=\n\d{1,2}\s*\.\s*\n|Author:|$)"
            matches = re.findall(pattern, body_text, re.DOTALL)

            for q_num_str, block in matches:
                q_num = int(q_num_str)
                q = self._parse_question_text(f"{q_num} . {block}", q_num, category)
                if q:
                    questions.append(q)

        except Exception as e:
            logger.warning(f"Alternative extraction failed: {e}")

        return questions

    def _parse_question_text(
        self, text: str, q_num: int, category: str
    ) -> RawQuestion | None:
        """Parse question text to extract question and options."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        if len(lines) < 2:
            return None

        # First line(s) contain the question number and text
        question_text = ""
        options = []
        option_start_idx = -1

        for i, line in enumerate(lines):
            # Skip the question number line
            if re.match(r"^\d{1,2}\s*\.$", line):
                continue

            # Check if this looks like an option (short text, not a question)
            # Options are typically shorter and don't end with question marks
            is_option = (
                len(line) < 50 and
                not line.endswith("?") and
                not any(kw in line.lower() for kw in ["rearrange", "sentence", "below", "which", "what", "find"])
            )

            if is_option and question_text:
                if option_start_idx < 0:
                    option_start_idx = i
                options.append(line)
            elif option_start_idx < 0:
                # Still building question text
                if question_text:
                    question_text += " " + line
                else:
                    question_text = line

        # Validate
        if not question_text or len(options) < 2:
            return None

        # Limit to 4 options
        options = options[:4]

        return RawQuestion(
            question_text=question_text,
            options=options,
            correct_answer=options[0],  # Will need verification
            explanation="",
            source_category=category,
        )

    def _extract_category_from_url(self, url: str) -> str:
        """Extract category from URL path."""
        match = re.search(r"/([^/]+?)/?$", url)
        if match:
            quiz_name = match.group(1).replace("-", " ").lower()
            for pattern, cat_type in self.CATEGORY_PATTERNS.items():
                if pattern in quiz_name:
                    return cat_type
        return ""

    async def crawl(self, subject: str) -> CrawlResult:
        """Crawl all quizzes for a subject.

        Args:
            subject: Subject to crawl

        Returns:
            CrawlResult with all extracted questions
        """
        result = CrawlResult(
            source=self.SOURCE_NAME,
            subject=subject,
            questions=[],
            started_at=datetime.utcnow(),
        )

        # Get quiz URLs
        logger.info(f"Getting quiz URLs for {subject}...")
        try:
            urls = await self.get_quiz_urls(subject)
            result.total_urls_found = len(urls)
            logger.info(f"Found {len(urls)} quiz URLs")
        except Exception as e:
            error_msg = f"Failed to get quiz URLs: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            result.completed_at = datetime.utcnow()
            return result

        # Create a single page for all requests (more efficient)
        page = await self._browser.new_page()

        try:
            for i, url in enumerate(urls, 1):
                logger.info(f"Crawling quiz {i}/{len(urls)}: {url}")

                try:
                    await self._rate_limit()
                    await page.goto(url, wait_until="networkidle")
                    await page.wait_for_timeout(500)  # Wait for JS

                    result.total_urls_crawled += 1
                    questions = await self.parse_quiz(page, url)

                    for q in questions:
                        q.source_url = url
                        q.source_name = self.SOURCE_NAME
                        result.questions.append(q)

                    logger.info(f"  Extracted {len(questions)} questions")

                except Exception as e:
                    error_msg = f"Error crawling {url}: {e}"
                    logger.error(error_msg)
                    result.errors.append(error_msg)

        finally:
            await page.close()

        result.total_questions_extracted = len(result.questions)
        result.completed_at = datetime.utcnow()

        logger.info(result.summary())
        return result
