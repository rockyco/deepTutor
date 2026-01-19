"""Progress and practice session models."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .question import Subject, QuestionType


class UserAnswer(BaseModel):
    """A single answer submitted by a user."""

    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    question_id: UUID
    user_answer: str | list[str] | dict[str, str]
    is_correct: bool
    time_taken_seconds: int
    hints_used: int = 0
    score: float = Field(ge=0, le=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PracticeSession(BaseModel):
    """A practice session containing multiple questions."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    subject: Subject | None = Field(default=None, description="None for mixed practice")
    question_type: QuestionType | None = Field(default=None, description="Specific type practice")
    is_timed: bool = False
    time_limit_minutes: int | None = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    question_ids: list[UUID] = Field(default_factory=list)
    answers: list[UserAnswer] = Field(default_factory=list)

    @property
    def total_questions(self) -> int:
        return len(self.question_ids)

    @property
    def questions_answered(self) -> int:
        return len(self.answers)

    @property
    def correct_answers(self) -> int:
        return sum(1 for a in self.answers if a.is_correct)

    @property
    def accuracy(self) -> float:
        if not self.answers:
            return 0.0
        return self.correct_answers / len(self.answers)

    @property
    def total_score(self) -> float:
        if not self.answers:
            return 0.0
        return sum(a.score for a in self.answers) / len(self.answers)


class PracticeSessionCreate(BaseModel):
    """Model for starting a new practice session."""

    subject: Subject | None = None
    question_type: QuestionType | None = None
    num_questions: int = Field(default=10, ge=1, le=50)
    difficulty: int | None = Field(default=None, ge=1, le=5)
    is_timed: bool = False
    time_limit_minutes: int | None = None


class PracticeSessionResult(BaseModel):
    """Results summary for a completed practice session."""

    session_id: UUID
    subject: Subject | None
    total_questions: int
    correct_answers: int
    accuracy: float
    total_score: float
    time_taken_minutes: float
    questions_by_type: dict[str, dict[str, int]]  # type -> {attempted, correct}
    strengths: list[str]
    areas_to_improve: list[str]


class Progress(BaseModel):
    """User's progress for a specific subject/question type."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    subject: Subject
    question_type: QuestionType
    total_attempted: int = 0
    total_correct: int = 0
    current_level: int = Field(default=1, ge=1, le=5)
    mastery_score: float = Field(default=0.0, ge=0, le=1)
    last_practiced: datetime | None = None
    streak: int = 0

    @property
    def accuracy(self) -> float:
        if self.total_attempted == 0:
            return 0.0
        return self.total_correct / self.total_attempted


class ProgressSummary(BaseModel):
    """Overall progress summary for a user."""

    user_id: UUID
    overall_mastery: float
    subjects: dict[str, dict]  # subject -> {mastery, accuracy, questions_done}
    weak_areas: list[dict]  # [{subject, type, accuracy}]
    strong_areas: list[dict]
    recent_activity: list[dict]
    recommended_next: list[dict]
