"""Crawler package for fetching questions from external sources."""

from .base import BaseCrawler
from .converter import QuestionConverter
from .education_quizzes import EducationQuizzesCrawler
from .education_quizzes_playwright import EducationQuizzesPlaywrightCrawler
from .eleven_plus_exams import ElevenPlusExamsCrawler
from .examberry import ExamBerryCrawler
from .models import CrawlResult, RawQuestion
from .nvr_shapes import NVRShapesCrawler
from .orchestrator import CrawlOrchestrator, run_full_crawl
from .pdf_extractor import PDFExtractor
from .sats_papers import SATSPapersCrawler
from .validator import QuestionValidator

__all__ = [
    # Base classes
    "BaseCrawler",
    "RawQuestion",
    "CrawlResult",
    # Crawlers
    "EducationQuizzesCrawler",
    "EducationQuizzesPlaywrightCrawler",
    "SATSPapersCrawler",
    "ElevenPlusExamsCrawler",
    "ExamBerryCrawler",
    "NVRShapesCrawler",
    # Utilities
    "PDFExtractor",
    "QuestionConverter",
    "QuestionValidator",
    # Orchestration
    "CrawlOrchestrator",
    "run_full_crawl",
]
