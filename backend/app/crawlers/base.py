"""Abstract base class for web crawlers."""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from .models import CrawlResult, RawQuestion

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """Base crawler with rate limiting, retries, and polite behavior.

    Subclasses must implement:
    - get_quiz_urls(): Return list of quiz page URLs to crawl
    - parse_quiz(): Extract questions from a quiz page
    """

    # Default settings - override in subclasses
    BASE_URL: str = ""
    SOURCE_NAME: str = "unknown"
    REQUEST_DELAY: float = 2.0  # seconds between requests
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 5.0  # seconds between retries
    TIMEOUT: float = 30.0

    USER_AGENT = (
        "Mozilla/5.0 (compatible; DeepTutorBot/1.0; "
        "+https://github.com/deeptutor; educational research)"
    )

    def __init__(
        self,
        request_delay: float | None = None,
        max_retries: int | None = None,
    ):
        """Initialize crawler with optional configuration overrides."""
        self.request_delay = request_delay or self.REQUEST_DELAY
        self.max_retries = max_retries or self.MAX_RETRIES
        self._last_request_time: float = 0

    async def _rate_limit(self) -> None:
        """Ensure minimum delay between requests."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        if elapsed < self.request_delay:
            await asyncio.sleep(self.request_delay - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    async def fetch(self, url: str) -> str | None:
        """Fetch URL with rate limiting and retries.

        Returns HTML content or None on failure.
        """
        await self._rate_limit()

        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-GB,en;q=0.9",
        }

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(
                    timeout=self.TIMEOUT,
                    follow_redirects=True,
                ) as client:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    logger.debug(f"Fetched {url} (attempt {attempt + 1})")
                    return response.text

            except httpx.TimeoutException:
                logger.warning(f"Timeout fetching {url} (attempt {attempt + 1})")
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP {e.response.status_code} for {url}")
                if e.response.status_code == 404:
                    return None  # Don't retry 404s
            except httpx.RequestError as e:
                logger.warning(f"Request error for {url}: {e}")

            if attempt < self.max_retries - 1:
                delay = self.RETRY_DELAY * (attempt + 1)  # Exponential backoff
                logger.info(f"Retrying in {delay}s...")
                await asyncio.sleep(delay)

        logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
        return None

    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content with lxml parser."""
        return BeautifulSoup(html, "lxml")

    @abstractmethod
    async def get_quiz_urls(self, subject: str) -> list[str]:
        """Get list of quiz page URLs for a subject.

        Args:
            subject: Subject identifier (e.g., 'verbal_reasoning')

        Returns:
            List of quiz page URLs to crawl
        """
        pass

    @abstractmethod
    async def parse_quiz(self, url: str, html: str) -> list[RawQuestion]:
        """Extract questions from a quiz page.

        Args:
            url: The quiz page URL
            html: The HTML content of the page

        Returns:
            List of extracted RawQuestion objects
        """
        pass

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

        # Crawl each quiz
        for i, url in enumerate(urls, 1):
            logger.info(f"Crawling quiz {i}/{len(urls)}: {url}")

            try:
                html = await self.fetch(url)
                if html is None:
                    result.errors.append(f"Failed to fetch: {url}")
                    continue

                result.total_urls_crawled += 1
                questions = await self.parse_quiz(url, html)

                for q in questions:
                    q.source_url = url
                    q.source_name = self.SOURCE_NAME
                    result.questions.append(q)

                logger.info(f"  Extracted {len(questions)} questions")

            except Exception as e:
                error_msg = f"Error parsing {url}: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)

        result.total_questions_extracted = len(result.questions)
        result.completed_at = datetime.utcnow()

        logger.info(result.summary())
        return result
