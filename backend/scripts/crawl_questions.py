#!/usr/bin/env python3
"""CLI script to crawl questions from external sources.

Usage:
    uv run python scripts/crawl_questions.py --source educationquizzes --subject all
    uv run python scripts/crawl_questions.py --subject verbal_reasoning --dry-run
    uv run python scripts/crawl_questions.py --subject maths --import-to-db
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.crawlers import (
    EducationQuizzesCrawler,
    QuestionConverter,
    QuestionValidator,
)
from app.crawlers.education_quizzes_playwright import EducationQuizzesPlaywrightCrawler
from app.models.question import Subject

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Available sources - Playwright version handles JS-rendered content
CRAWLERS = {
    "educationquizzes": EducationQuizzesPlaywrightCrawler,
    "educationquizzes-static": EducationQuizzesCrawler,
}

# Subject mapping
SUBJECTS = {
    "verbal_reasoning": "verbal_reasoning",
    "non_verbal_reasoning": "non_verbal_reasoning",
    "maths": "maths",
    "english": "english",
    "all": None,  # Special case: crawl all subjects
}


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Crawl questions from external sources to enrich the question library.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what would be crawled (no actual crawling)
  uv run python scripts/crawl_questions.py --subject verbal_reasoning --dry-run

  # Crawl verbal reasoning questions
  uv run python scripts/crawl_questions.py --source educationquizzes --subject verbal_reasoning

  # Crawl all subjects
  uv run python scripts/crawl_questions.py --subject all

  # Crawl and import to database
  uv run python scripts/crawl_questions.py --subject maths --import-to-db
        """,
    )

    parser.add_argument(
        "--source",
        choices=list(CRAWLERS.keys()),
        default="educationquizzes",
        help="Source site to crawl (default: educationquizzes)",
    )

    parser.add_argument(
        "--subject",
        choices=list(SUBJECTS.keys()),
        required=True,
        help="Subject to crawl, or 'all' for all subjects",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually crawling",
    )

    parser.add_argument(
        "--import-to-db",
        action="store_true",
        help="Import crawled questions directly to the database",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/crawled"),
        help="Directory to save crawled data (default: data/crawled)",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between requests in seconds (default: 2.0)",
    )

    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip validation step (not recommended)",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )

    return parser.parse_args()


async def crawl_subject(
    crawler_class: type,
    subject: str,
    args: argparse.Namespace,
    crawler_instance=None,
) -> dict | None:
    """Crawl a single subject and return results.

    Args:
        crawler_class: Crawler class to use
        subject: Subject string
        args: Parsed command line arguments
        crawler_instance: Pre-initialized crawler (for Playwright reuse)

    Returns:
        Dict with crawl results, or None on failure
    """
    logger.info(f"Starting crawl for {subject}...")

    # Use provided instance or create new one
    crawler = crawler_instance or crawler_class(request_delay=args.delay)

    # Crawl - Playwright crawlers need context manager if not pre-initialized
    if crawler_instance:
        result = await crawler.crawl(subject)
    elif hasattr(crawler_class, "__aenter__"):
        # Playwright-based crawler
        async with crawler_class(request_delay=args.delay) as crawler:
            result = await crawler.crawl(subject)
    else:
        # Static HTTP crawler
        result = await crawler.crawl(subject)

    if not result.questions:
        logger.warning(f"No questions found for {subject}")
        return None

    logger.info(result.summary())

    # Convert to app format
    converter = QuestionConverter(source_name=f"crawled-{crawler.SOURCE_NAME}")
    converted = converter.convert_result(result)

    logger.info(f"Converted {len(converted['questions'])} questions")

    # Validate unless skipped
    if not args.skip_validation:
        validator = QuestionValidator()
        valid, invalid = validator.validate_questions(converted["questions"])

        if invalid:
            logger.warning(f"Found {len(invalid)} invalid questions")
            if args.verbose:
                for q in invalid[:5]:  # Show first 5
                    errors = q.get("_validation_errors", [])
                    logger.warning(f"  - {errors}")

        # Deduplicate
        unique, num_dupes = validator.deduplicate(valid)
        if num_dupes:
            logger.info(f"Removed {num_dupes} duplicate questions")

        converted["questions"] = unique
        converted["metadata"]["validation"] = {
            "total_valid": len(valid),
            "total_invalid": len(invalid),
            "duplicates_removed": num_dupes,
            "final_count": len(unique),
        }

    return converted


async def main():
    """Main entry point."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine subjects to crawl
    if args.subject == "all":
        subjects_to_crawl = ["verbal_reasoning", "non_verbal_reasoning", "maths", "english"]
    else:
        subjects_to_crawl = [args.subject]

    # Get crawler class
    crawler_class = CRAWLERS[args.source]

    # Dry run mode
    if args.dry_run:
        print("\n=== DRY RUN MODE ===")
        print(f"Source: {args.source}")
        print(f"Subjects: {', '.join(subjects_to_crawl)}")
        print(f"Output directory: {args.output_dir}")
        print(f"Request delay: {args.delay}s")
        print()

        # Show what URLs would be crawled
        crawler = crawler_class(request_delay=args.delay)
        for subject in subjects_to_crawl:
            print(f"\n{subject}:")
            print(f"  Listing URL: {crawler.BASE_URL}/{crawler.SUBJECT_PATHS.get(subject, '?')}/")

        print("\nRun without --dry-run to perform actual crawl.")
        return

    # Ensure output directory exists
    output_dir = Path(__file__).parent.parent / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Crawl each subject
    all_results = {}
    total_questions = 0

    # Use context manager for Playwright-based crawlers to share browser instance
    if hasattr(crawler_class, "__aenter__"):
        async with crawler_class(request_delay=args.delay) as crawler:
            for subject in subjects_to_crawl:
                result = await crawl_subject(crawler_class, subject, args, crawler_instance=crawler)
                if result:
                    all_results[subject] = result
                    total_questions += len(result["questions"])

                    # Save to file
                    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    filename = f"{args.source}_{subject}_{timestamp}.json"
                    output_path = output_dir / filename

                    with open(output_path, "w") as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)

                    logger.info(f"Saved {len(result['questions'])} questions to {output_path}")
    else:
        # Static HTTP crawler
        for subject in subjects_to_crawl:
            result = await crawl_subject(crawler_class, subject, args)
            if result:
                all_results[subject] = result
                total_questions += len(result["questions"])

                # Save to file
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = f"{args.source}_{subject}_{timestamp}.json"
                output_path = output_dir / filename

                with open(output_path, "w") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

                logger.info(f"Saved {len(result['questions'])} questions to {output_path}")

    # Summary
    print("\n" + "=" * 60)
    print("CRAWL SUMMARY")
    print("=" * 60)
    for subject, result in all_results.items():
        meta = result.get("metadata", {})
        print(f"\n{subject}:")
        print(f"  Crawled: {meta.get('total_crawled', 0)}")
        print(f"  Converted: {meta.get('total_converted', 0)}")
        if "validation" in meta:
            print(f"  Valid: {meta['validation']['total_valid']}")
            print(f"  Final: {meta['validation']['final_count']}")

    print(f"\nTotal questions: {total_questions}")
    print(f"Output directory: {output_dir}")

    # Import to database if requested
    if args.import_to_db and total_questions > 0:
        print("\nImporting to database...")
        await import_to_database(all_results)


async def import_to_database(results: dict[str, dict]) -> None:
    """Import crawled questions to the database.

    Args:
        results: Dict of subject -> crawl results
    """
    from app.db import async_session, init_db
    from app.services.question_bank import QuestionBankService
    from app.models.question import (
        Answer,
        Hint,
        QuestionContent,
        QuestionCreate,
        QuestionFormat,
        QuestionType,
        Subject,
    )

    await init_db()

    total_imported = 0

    async with async_session() as db:
        service = QuestionBankService(db)

        for subject, result in results.items():
            questions = result.get("questions", [])
            subject_count = 0

            for q_data in questions:
                try:
                    question = QuestionCreate(
                        subject=Subject(q_data["subject"]),
                        question_type=QuestionType(q_data["question_type"]),
                        format=QuestionFormat(q_data.get("format", "multiple_choice")),
                        difficulty=q_data.get("difficulty", 3),
                        content=QuestionContent(**q_data["content"]),
                        answer=Answer(**q_data["answer"]),
                        explanation=q_data["explanation"],
                        hints=[Hint(**h) for h in q_data.get("hints", [])],
                        tags=q_data.get("tags", []),
                        source=q_data.get("source"),
                    )
                    await service.create_question(question)
                    subject_count += 1
                except Exception as e:
                    logger.error(f"Failed to import question: {e}")

            logger.info(f"Imported {subject_count} questions for {subject}")
            total_imported += subject_count

        await db.commit()

    print(f"\nImported {total_imported} questions to database")


if __name__ == "__main__":
    asyncio.run(main())
