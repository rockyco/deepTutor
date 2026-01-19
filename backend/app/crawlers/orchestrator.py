"""Crawl orchestrator for managing multiple crawl sources.

Coordinates crawling across multiple sources, handles deduplication,
validation, and database import.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .converter import QuestionConverter
from .education_quizzes import EducationQuizzesCrawler
from .eleven_plus_exams import ElevenPlusExamsCrawler
from .examberry import ExamBerryCrawler
from .models import CrawlResult, RawQuestion
from .nvr_shapes import NVRShapesCrawler
from .sats_papers import SATSPapersCrawler
from .validator import QuestionValidator

logger = logging.getLogger(__name__)


class CrawlOrchestrator:
    """Orchestrates crawling from multiple sources.

    Features:
    - Parallel crawling from multiple sources
    - Automatic deduplication
    - Quality validation
    - Database import
    - Progress tracking and reporting
    """

    # Available crawlers by source name
    CRAWLERS = {
        "education_quizzes": EducationQuizzesCrawler,
        "sats_papers": SATSPapersCrawler,
        "eleven_plus_exams": ElevenPlusExamsCrawler,
        "examberry": ExamBerryCrawler,
        "nvr_shapes": NVRShapesCrawler,
    }

    # Default subjects per crawler
    CRAWLER_SUBJECTS = {
        "education_quizzes": ["verbal_reasoning", "maths", "english"],
        "sats_papers": ["verbal_reasoning", "maths", "english", "non_verbal_reasoning"],
        "eleven_plus_exams": ["verbal_reasoning"],
        "examberry": ["verbal_reasoning", "maths", "english", "non_verbal_reasoning"],
        "nvr_shapes": ["non_verbal_reasoning"],
    }

    def __init__(
        self,
        output_dir: str = "backend/data/crawled",
        db_path: str = "backend/data/tutor.db",
    ):
        """Initialize orchestrator.

        Args:
            output_dir: Directory to save crawled data
            db_path: Path to SQLite database for import
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path)

        self.validator = QuestionValidator()
        self.converter = QuestionConverter()

        # Track overall progress
        self._results: list[CrawlResult] = []
        self._all_questions: list[dict[str, Any]] = []

    async def crawl_all_sources(
        self,
        sources: list[str] | None = None,
        subjects: list[str] | None = None,
        parallel: bool = False,
    ) -> dict[str, Any]:
        """Crawl all configured sources.

        Args:
            sources: Specific sources to crawl (None = all)
            subjects: Specific subjects to crawl (None = all per source)
            parallel: Whether to crawl sources in parallel

        Returns:
            Summary dict with stats and results
        """
        started_at = datetime.utcnow()
        sources = sources or list(self.CRAWLERS.keys())

        logger.info(f"Starting crawl of {len(sources)} sources")

        if parallel:
            tasks = []
            for source in sources:
                source_subjects = subjects or self.CRAWLER_SUBJECTS.get(source, [])
                tasks.append(self._crawl_source(source, source_subjects))
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for r in results:
                if isinstance(r, Exception):
                    logger.error(f"Crawl error: {r}")
                elif r:
                    self._results.extend(r)
        else:
            for source in sources:
                source_subjects = subjects or self.CRAWLER_SUBJECTS.get(source, [])
                try:
                    results = await self._crawl_source(source, source_subjects)
                    self._results.extend(results)
                except Exception as e:
                    logger.error(f"Failed to crawl {source}: {e}")

        # Process all results
        summary = await self._process_results()
        summary["crawl_time"] = (datetime.utcnow() - started_at).total_seconds()
        summary["sources_crawled"] = sources

        return summary

    async def _crawl_source(
        self, source: str, subjects: list[str]
    ) -> list[CrawlResult]:
        """Crawl a single source for specified subjects."""
        if source not in self.CRAWLERS:
            logger.warning(f"Unknown source: {source}")
            return []

        crawler_class = self.CRAWLERS[source]
        crawler = crawler_class()
        results = []

        for subject in subjects:
            logger.info(f"Crawling {source} - {subject}")
            try:
                result = await crawler.crawl(subject)
                results.append(result)

                # Save raw results
                self._save_raw_results(result)

            except Exception as e:
                logger.error(f"Error crawling {source}/{subject}: {e}")

        return results

    def _save_raw_results(self, result: CrawlResult) -> None:
        """Save raw crawl results to file."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{result.source}_{result.subject}_{timestamp}.json"
        filepath = self.output_dir / filename

        data = {
            "source": result.source,
            "subject": result.subject,
            "crawled_at": result.started_at.isoformat(),
            "total_questions": len(result.questions),
            "errors": result.errors,
            "questions": [q.to_dict() for q in result.questions],
        }

        filepath.write_text(json.dumps(data, indent=2))
        logger.info(f"Saved raw results to {filepath}")

    async def _process_results(self) -> dict[str, Any]:
        """Process all crawl results: convert, validate, deduplicate."""
        total_raw = 0
        converted_questions = []

        # Convert all raw questions
        for result in self._results:
            total_raw += len(result.questions)

            converted = self.converter.convert_result(result)
            converted_questions.extend(converted["questions"])

        logger.info(f"Total raw questions: {total_raw}")
        logger.info(f"Converted questions: {len(converted_questions)}")

        # Validate
        valid, invalid = self.validator.validate_questions(converted_questions)
        logger.info(f"Valid: {len(valid)}, Invalid: {len(invalid)}")

        # Deduplicate
        unique, num_duplicates = self.validator.deduplicate(valid)
        logger.info(f"Unique: {len(unique)}, Duplicates removed: {num_duplicates}")

        # Quality filter
        high_quality, low_quality = self.validator.filter_by_quality(unique)
        logger.info(f"High quality: {len(high_quality)}, Low quality: {len(low_quality)}")

        self._all_questions = high_quality

        return {
            "total_raw": total_raw,
            "total_converted": len(converted_questions),
            "total_valid": len(valid),
            "total_invalid": len(invalid),
            "total_unique": len(unique),
            "duplicates_removed": num_duplicates,
            "high_quality": len(high_quality),
            "low_quality": len(low_quality),
        }

    async def crawl_pdfs_from_urls(
        self, urls: list[str], source_name: str = "manual"
    ) -> CrawlResult:
        """Crawl questions from a list of PDF URLs.

        Args:
            urls: List of PDF URLs to process
            source_name: Source name for attribution

        Returns:
            CrawlResult with extracted questions
        """
        from .pdf_extractor import PDFExtractor

        extractor = PDFExtractor()
        result = CrawlResult(
            source=source_name,
            subject="mixed",
            questions=[],
            total_urls_found=len(urls),
            started_at=datetime.utcnow(),
        )

        for url in urls:
            try:
                questions = await extractor.extract_questions_from_url(
                    url, source_name=source_name
                )
                result.total_urls_crawled += 1

                for q in questions:
                    q.source_url = url
                    result.questions.append(q)

                logger.info(f"Extracted {len(questions)} questions from {url}")

            except Exception as e:
                error_msg = f"Error processing {url}: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)

        result.total_questions_extracted = len(result.questions)
        result.completed_at = datetime.utcnow()

        return result

    async def import_to_database(self) -> dict[str, Any]:
        """Import processed questions to database.

        Returns:
            Import stats
        """
        if not self._all_questions:
            logger.warning("No questions to import")
            return {"imported": 0, "errors": 0}

        # Import logic depends on your database setup
        # This is a placeholder for the actual import
        imported = 0
        errors = 0

        try:
            # Example: Direct SQLite import
            import sqlite3

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            for q in self._all_questions:
                try:
                    # Check if question already exists
                    cursor.execute(
                        "SELECT id FROM questions WHERE content = ?",
                        (json.dumps(q["content"]),)
                    )
                    if cursor.fetchone():
                        continue

                    # Insert new question
                    cursor.execute(
                        """
                        INSERT INTO questions
                        (subject, question_type, format, difficulty, content,
                         answer, explanation, hints, tags, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            q["subject"],
                            q["question_type"],
                            q.get("format", "multiple_choice"),
                            q.get("difficulty", 3),
                            json.dumps(q["content"]),
                            json.dumps(q["answer"]),
                            q.get("explanation", ""),
                            json.dumps(q.get("hints", [])),
                            json.dumps(q.get("tags", [])),
                            q.get("source", ""),
                        )
                    )
                    imported += 1

                except Exception as e:
                    logger.warning(f"Failed to import question: {e}")
                    errors += 1

            conn.commit()
            conn.close()

            logger.info(f"Imported {imported} questions, {errors} errors")

        except Exception as e:
            logger.error(f"Database import failed: {e}")
            errors += 1

        return {"imported": imported, "errors": errors}

    def get_questions_by_type(self) -> dict[str, int]:
        """Get count of questions by type."""
        counts: dict[str, int] = {}

        for q in self._all_questions:
            q_type = q.get("question_type", "unknown")
            counts[q_type] = counts.get(q_type, 0) + 1

        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    def get_questions_by_subject(self) -> dict[str, int]:
        """Get count of questions by subject."""
        counts: dict[str, int] = {}

        for q in self._all_questions:
            subject = q.get("subject", "unknown")
            counts[subject] = counts.get(subject, 0) + 1

        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    def export_questions(
        self, filepath: str | Path, format: str = "json"
    ) -> None:
        """Export processed questions to file.

        Args:
            filepath: Output file path
            format: Export format ('json' or 'jsonl')
        """
        filepath = Path(filepath)

        if format == "json":
            filepath.write_text(json.dumps(self._all_questions, indent=2))
        elif format == "jsonl":
            with filepath.open("w") as f:
                for q in self._all_questions:
                    f.write(json.dumps(q) + "\n")
        else:
            raise ValueError(f"Unknown format: {format}")

        logger.info(f"Exported {len(self._all_questions)} questions to {filepath}")


async def run_full_crawl(
    sources: list[str] | None = None,
    subjects: list[str] | None = None,
    import_to_db: bool = True,
    parallel: bool = False,
) -> dict[str, Any]:
    """Convenience function to run a full crawl.

    Args:
        sources: Sources to crawl (None = all)
        subjects: Subjects to crawl (None = default per source)
        import_to_db: Whether to import to database
        parallel: Whether to crawl in parallel

    Returns:
        Summary dict with all stats
    """
    orchestrator = CrawlOrchestrator()

    # Run crawl
    summary = await orchestrator.crawl_all_sources(
        sources=sources,
        subjects=subjects,
        parallel=parallel,
    )

    # Export questions
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    orchestrator.export_questions(f"backend/data/crawled/all_questions_{timestamp}.json")

    # Print stats
    print("\n" + "=" * 50)
    print("CRAWL SUMMARY")
    print("=" * 50)
    print(f"Total raw questions:    {summary['total_raw']}")
    print(f"Total converted:        {summary['total_converted']}")
    print(f"Total valid:            {summary['total_valid']}")
    print(f"Total unique:           {summary['total_unique']}")
    print(f"High quality:           {summary['high_quality']}")
    print(f"Crawl time:             {summary['crawl_time']:.1f}s")
    print()

    print("Questions by Subject:")
    for subject, count in orchestrator.get_questions_by_subject().items():
        print(f"  {subject}: {count}")
    print()

    print("Questions by Type (top 10):")
    type_counts = orchestrator.get_questions_by_type()
    for q_type, count in list(type_counts.items())[:10]:
        print(f"  {q_type}: {count}")

    # Import to database
    if import_to_db:
        print("\nImporting to database...")
        import_result = await orchestrator.import_to_database()
        summary["import"] = import_result
        print(f"Imported: {import_result['imported']}, Errors: {import_result['errors']}")

    return summary
