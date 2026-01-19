"""Data models for crawler operations."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RawQuestion:
    """Raw question data as extracted from source sites.

    This is a flexible container for crawled data before conversion
    to the app's Question schema.
    """

    question_text: str
    options: list[str]
    correct_answer: str
    explanation: str = ""

    # Metadata from source
    source_url: str = ""
    source_name: str = ""
    source_category: str = ""
    source_subcategory: str = ""

    # Additional data that may be present
    image_urls: list[str] = field(default_factory=list)
    additional_context: str = ""
    raw_html: str = ""

    # Crawl metadata
    crawled_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "question_text": self.question_text,
            "options": self.options,
            "correct_answer": self.correct_answer,
            "explanation": self.explanation,
            "source_url": self.source_url,
            "source_name": self.source_name,
            "source_category": self.source_category,
            "source_subcategory": self.source_subcategory,
            "image_urls": self.image_urls,
            "additional_context": self.additional_context,
            "crawled_at": self.crawled_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RawQuestion":
        """Create from dictionary."""
        crawled_at = data.get("crawled_at")
        if isinstance(crawled_at, str):
            crawled_at = datetime.fromisoformat(crawled_at)

        return cls(
            question_text=data["question_text"],
            options=data["options"],
            correct_answer=data["correct_answer"],
            explanation=data.get("explanation", ""),
            source_url=data.get("source_url", ""),
            source_name=data.get("source_name", ""),
            source_category=data.get("source_category", ""),
            source_subcategory=data.get("source_subcategory", ""),
            image_urls=data.get("image_urls", []),
            additional_context=data.get("additional_context", ""),
            crawled_at=crawled_at or datetime.utcnow(),
        )


@dataclass
class CrawlResult:
    """Result of a crawl operation."""

    source: str
    subject: str
    questions: list[RawQuestion]

    # Stats
    total_urls_found: int = 0
    total_urls_crawled: int = 0
    total_questions_extracted: int = 0
    errors: list[str] = field(default_factory=list)

    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    @property
    def duration_seconds(self) -> float:
        """Get crawl duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0

    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.total_urls_crawled == 0:
            return 0.0
        return (len(self.questions) / self.total_urls_crawled) * 100

    def summary(self) -> str:
        """Get human-readable summary."""
        lines = [
            f"Crawl Result: {self.source} - {self.subject}",
            f"  URLs found: {self.total_urls_found}",
            f"  URLs crawled: {self.total_urls_crawled}",
            f"  Questions extracted: {len(self.questions)}",
            f"  Success rate: {self.success_rate:.1f}%",
            f"  Duration: {self.duration_seconds:.1f}s",
        ]
        if self.errors:
            lines.append(f"  Errors: {len(self.errors)}")
        return "\n".join(lines)
