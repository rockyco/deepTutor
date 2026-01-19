#!/usr/bin/env python3
"""CLI script to run question crawlers.

Usage:
    uv run python scripts/crawl_all.py                    # Crawl all sources
    uv run python scripts/crawl_all.py --sources sats_papers examberry
    uv run python scripts/crawl_all.py --subjects verbal_reasoning maths
    uv run python scripts/crawl_all.py --parallel         # Crawl in parallel
    uv run python scripts/crawl_all.py --no-import        # Don't import to DB
    uv run python scripts/crawl_all.py --pdf-urls urls.txt  # Crawl from URL list
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.crawlers.orchestrator import CrawlOrchestrator, run_full_crawl


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("crawl.log"),
        ]
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Crawl 11+ question sources and import to database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Crawl all sources
  %(prog)s --sources sats_papers examberry    # Specific sources
  %(prog)s --subjects verbal_reasoning        # Specific subject
  %(prog)s --parallel --no-import             # Fast crawl, no DB import
  %(prog)s --pdf-urls papers.txt              # Crawl PDF URLs from file

Available sources:
  - education_quizzes    educationquizzes.com (HTML quizzes)
  - sats_papers          sats-papers.co.uk (PDF papers)
  - eleven_plus_exams    elevenplusexams.co.uk (mixed)
  - examberry            examberrypapers.co.uk (PDF papers)
  - nvr_shapes           NVR-focused multi-source crawler

Available subjects:
  - verbal_reasoning
  - non_verbal_reasoning
  - maths
  - english
        """
    )

    parser.add_argument(
        "--sources", "-s",
        nargs="+",
        choices=[
            "education_quizzes",
            "sats_papers",
            "eleven_plus_exams",
            "examberry",
            "nvr_shapes",
        ],
        help="Specific sources to crawl (default: all)"
    )

    parser.add_argument(
        "--subjects",
        nargs="+",
        choices=[
            "verbal_reasoning",
            "non_verbal_reasoning",
            "maths",
            "english",
        ],
        help="Specific subjects to crawl (default: all per source)"
    )

    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Crawl sources in parallel (faster but more load)"
    )

    parser.add_argument(
        "--no-import",
        action="store_true",
        help="Don't import to database (just crawl and save)"
    )

    parser.add_argument(
        "--pdf-urls",
        type=str,
        help="File containing PDF URLs to crawl (one per line)"
    )

    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default="backend/data/crawled",
        help="Output directory for crawled data"
    )

    parser.add_argument(
        "--db-path",
        type=str,
        default="backend/data/tutor.db",
        help="Path to SQLite database"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be crawled without actually crawling"
    )

    return parser.parse_args()


async def crawl_pdf_urls(
    filepath: str,
    output_dir: str,
    import_to_db: bool,
    db_path: str,
) -> None:
    """Crawl questions from a list of PDF URLs."""
    path = Path(filepath)
    if not path.exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    urls = [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

    print(f"Found {len(urls)} PDF URLs to crawl")

    orchestrator = CrawlOrchestrator(
        output_dir=output_dir,
        db_path=db_path,
    )

    result = await orchestrator.crawl_pdfs_from_urls(urls)

    print(f"\nCrawled {result.total_urls_crawled} PDFs")
    print(f"Extracted {result.total_questions_extracted} questions")

    if result.errors:
        print(f"Errors: {len(result.errors)}")
        for error in result.errors[:5]:
            print(f"  - {error}")

    if import_to_db:
        # Process and import
        summary = await orchestrator._process_results()
        print(f"\nProcessed: {summary['high_quality']} high quality questions")

        import_result = await orchestrator.import_to_database()
        print(f"Imported: {import_result['imported']} questions")


async def main_async(args: argparse.Namespace) -> int:
    """Main async entry point."""
    if args.pdf_urls:
        await crawl_pdf_urls(
            args.pdf_urls,
            args.output_dir,
            not args.no_import,
            args.db_path,
        )
        return 0

    if args.dry_run:
        print("DRY RUN - Would crawl:")
        sources = args.sources or list(CrawlOrchestrator.CRAWLERS.keys())
        for source in sources:
            subjects = args.subjects or CrawlOrchestrator.CRAWLER_SUBJECTS.get(source, [])
            print(f"  {source}: {', '.join(subjects)}")
        return 0

    summary = await run_full_crawl(
        sources=args.sources,
        subjects=args.subjects,
        import_to_db=not args.no_import,
        parallel=args.parallel,
    )

    return 0 if summary else 1


def main() -> int:
    """Main entry point."""
    args = parse_args()
    setup_logging(args.verbose)

    print("=" * 60)
    print("11+ Question Crawler")
    print("=" * 60)

    if args.sources:
        print(f"Sources: {', '.join(args.sources)}")
    else:
        print("Sources: all")

    if args.subjects:
        print(f"Subjects: {', '.join(args.subjects)}")
    else:
        print("Subjects: default per source")

    print(f"Parallel: {args.parallel}")
    print(f"Import to DB: {not args.no_import}")
    print()

    try:
        return asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\nCrawl interrupted by user")
        return 130


if __name__ == "__main__":
    sys.exit(main())
