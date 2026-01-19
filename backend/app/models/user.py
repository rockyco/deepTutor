"""User-related Pydantic models."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Model for creating a new user."""

    name: str = Field(min_length=1, max_length=100)
    year_group: int = Field(default=5, ge=4, le=6)
    target_schools: list[str] = Field(default_factory=list)


class User(BaseModel):
    """Complete user model."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    year_group: int = 5
    target_schools: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)

    # Aggregated stats
    total_questions_attempted: int = 0
    total_correct: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    total_practice_time_minutes: int = 0

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Alex",
                "year_group": 5,
                "target_schools": ["King Edward's School", "Camp Hill"],
            }
        }


class UserStats(BaseModel):
    """Detailed statistics for a user."""

    user_id: UUID
    overall_accuracy: float = Field(ge=0, le=1)
    subject_accuracies: dict[str, float]
    weak_areas: list[str]
    strong_areas: list[str]
    recommended_practice: list[str]
    daily_goal_progress: float = Field(ge=0, le=1)
    weekly_practice_minutes: int
