"""SQLAlchemy database models."""

import json
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid4())


class UserDB(Base):
    """User database model."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    year_group: Mapped[int] = mapped_column(Integer, default=5)
    target_schools: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    total_questions_attempted: Mapped[int] = mapped_column(Integer, default=0)
    total_correct: Mapped[int] = mapped_column(Integer, default=0)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    total_practice_time_minutes: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    sessions: Mapped[list["PracticeSessionDB"]] = relationship(back_populates="user")
    progress: Mapped[list["ProgressDB"]] = relationship(back_populates="user")

    def get_target_schools(self) -> list[str]:
        return json.loads(self.target_schools)

    def set_target_schools(self, schools: list[str]) -> None:
        self.target_schools = json.dumps(schools)


class QuestionDB(Base):
    """Question database model."""

    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    subject: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    question_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    format: Mapped[str] = mapped_column(String(30), default="multiple_choice")
    difficulty: Mapped[int] = mapped_column(Integer, default=3)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    answer: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    hints: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    tags: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def get_content(self) -> dict:
        return json.loads(self.content)

    def set_content(self, content: dict) -> None:
        self.content = json.dumps(content)

    def get_answer(self) -> dict:
        return json.loads(self.answer)

    def set_answer(self, answer: dict) -> None:
        self.answer = json.dumps(answer)

    def get_hints(self) -> list:
        return json.loads(self.hints)

    def set_hints(self, hints: list) -> None:
        self.hints = json.dumps(hints)

    def get_tags(self) -> list[str]:
        return json.loads(self.tags)

    def set_tags(self, tags: list[str]) -> None:
        self.tags = json.dumps(tags)


class PracticeSessionDB(Base):
    """Practice session database model."""

    __tablename__ = "practice_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(50), nullable=True)
    question_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_timed: Mapped[bool] = mapped_column(Boolean, default=False)
    time_limit_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    question_ids: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    total_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Relationships
    user: Mapped["UserDB"] = relationship(back_populates="sessions")
    answers: Mapped[list["UserAnswerDB"]] = relationship(back_populates="session")

    def get_question_ids(self) -> list[str]:
        return json.loads(self.question_ids)

    def set_question_ids(self, ids: list[str]) -> None:
        self.question_ids = json.dumps(ids)


class UserAnswerDB(Base):
    """User answer database model."""

    __tablename__ = "user_answers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("practice_sessions.id"), nullable=False
    )
    question_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_answer: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    time_taken_seconds: Mapped[int] = mapped_column(Integer, default=0)
    hints_used: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    session: Mapped["PracticeSessionDB"] = relationship(back_populates="answers")


class ProgressDB(Base):
    """User progress database model."""

    __tablename__ = "progress"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    subject: Mapped[str] = mapped_column(String(50), nullable=False)
    question_type: Mapped[str] = mapped_column(String(50), nullable=False)
    total_attempted: Mapped[int] = mapped_column(Integer, default=0)
    total_correct: Mapped[int] = mapped_column(Integer, default=0)
    current_level: Mapped[int] = mapped_column(Integer, default=1)
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0)
    last_practiced: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    streak: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    user: Mapped["UserDB"] = relationship(back_populates="progress")

    # Unique constraint on user + subject + question_type
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )
