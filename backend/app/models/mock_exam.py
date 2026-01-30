"""Mock exam models for GL Assessment format.

Trafford Grammar School GL Assessment format:
- 2 papers per exam, same structure
- Each paper: 4 timed sections
  - English (comprehension + vocabulary): 12 + 8 = 20 questions, 15 minutes
  - Maths: 30 questions, 19 minutes
  - Non-verbal Reasoning: 20 questions, 8 minutes
  - Verbal Reasoning: 20 questions, 8 minutes
- Total: 90 questions per paper, 50 minutes per paper
"""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class ExamSection(str, Enum):
    ENGLISH = "english"
    MATHS = "maths"
    NON_VERBAL_REASONING = "non_verbal_reasoning"
    VERBAL_REASONING = "verbal_reasoning"


class SectionConfig(BaseModel):
    """Configuration for one section of a paper."""
    section: ExamSection
    question_count: int
    time_seconds: int
    subtypes: dict[str, int] | None = None  # e.g. {"comprehension": 12, "vocabulary": 8}


# GL Assessment paper structure
PAPER_SECTIONS: list[SectionConfig] = [
    SectionConfig(
        section=ExamSection.ENGLISH,
        question_count=20,
        time_seconds=900,  # 15 minutes
        subtypes={"comprehension": 12, "vocabulary": 8},
    ),
    SectionConfig(
        section=ExamSection.MATHS,
        question_count=30,
        time_seconds=1140,  # 19 minutes
    ),
    SectionConfig(
        section=ExamSection.NON_VERBAL_REASONING,
        question_count=20,
        time_seconds=480,  # 8 minutes
    ),
    SectionConfig(
        section=ExamSection.VERBAL_REASONING,
        question_count=20,
        time_seconds=480,  # 8 minutes
    ),
]

QUESTIONS_PER_PAPER = sum(s.question_count for s in PAPER_SECTIONS)  # 90
PAPERS_PER_EXAM = 2
TOTAL_QUESTIONS = QUESTIONS_PER_PAPER * PAPERS_PER_EXAM  # 180


class SectionQuestions(BaseModel):
    """Questions for a single section, returned to the frontend."""
    section: ExamSection
    section_index: int
    question_ids: list[str]
    question_count: int
    time_seconds: int


class PaperStructure(BaseModel):
    """Structure of one paper within a mock exam."""
    paper_number: int  # 1 or 2
    sections: list[SectionQuestions]
    total_questions: int = QUESTIONS_PER_PAPER


class MockExamSession(BaseModel):
    """A complete mock exam session."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    exam_number: int = 1  # Which exam (1, 2, or 3)
    papers: list[PaperStructure]
    status: str = "in_progress"  # in_progress, completed
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    answers: dict[str, str] = Field(default_factory=dict)  # question_id -> user_answer
    answer_times: dict[str, int] = Field(default_factory=dict)  # question_id -> seconds


class MockExamAnswer(BaseModel):
    """A single answer submission during a mock exam."""
    question_id: str
    user_answer: str
    time_taken_seconds: int = 0


class SectionResult(BaseModel):
    """Results for a single section."""
    section: ExamSection
    total: int
    correct: int
    accuracy: float
    time_used_seconds: int


class PaperResult(BaseModel):
    """Results for a single paper."""
    paper_number: int
    sections: list[SectionResult]
    total_questions: int
    total_correct: int
    accuracy: float
    total_time_seconds: int


class MockExamResult(BaseModel):
    """Complete results for a mock exam."""
    exam_id: str
    user_id: str
    papers: list[PaperResult]
    total_questions: int
    total_correct: int
    overall_accuracy: float
    total_time_seconds: int
    subject_breakdown: dict[str, dict[str, int | float]]
    completed_at: datetime
