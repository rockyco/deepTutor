"""Lessons API - serves static lesson content for the Learn section."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lessons", tags=["lessons"])

LESSONS_DIR = Path(__file__).parent.parent.parent / "data" / "lessons"

# Subject file mapping
SUBJECT_FILES = {
    "english": "english_lessons.json",
    "maths": "maths_lessons.json",
    "verbal_reasoning": "verbal_reasoning_lessons.json",
    "non_verbal_reasoning": "non_verbal_reasoning_lessons.json",
}

# In-memory cache (loaded once per process)
_cache: dict[str, list[dict]] = {}


def _load_subject(subject: str) -> list[dict]:
    """Load and cache lessons for a subject."""
    if subject in _cache:
        return _cache[subject]

    filename = SUBJECT_FILES.get(subject)
    if not filename:
        return []

    filepath = LESSONS_DIR / filename
    if not filepath.exists():
        logger.warning(f"Lesson file not found: {filepath}")
        return []

    with open(filepath) as f:
        lessons = json.load(f)

    _cache[subject] = lessons
    return lessons


def _lesson_summary(lesson: dict, subject: str) -> dict:
    """Extract summary fields for listing."""
    return {
        "subject": subject,
        "questionType": lesson["questionType"],
        "title": lesson["title"],
        "subtitle": lesson.get("subtitle", ""),
        "difficulty": lesson.get("difficulty", "foundation"),
        "color": lesson.get("color", "blue"),
        "sectionCount": len(lesson.get("sections", [])),
    }


@router.get("")
async def list_lessons():
    """List all available lessons across all subjects."""
    result = []
    for subject in SUBJECT_FILES:
        lessons = _load_subject(subject)
        for lesson in lessons:
            result.append(_lesson_summary(lesson, subject))
    return result


@router.get("/{subject}")
async def list_subject_lessons(subject: str):
    """List lessons for a specific subject."""
    if subject not in SUBJECT_FILES:
        raise HTTPException(status_code=404, detail=f"Unknown subject: {subject}")

    lessons = _load_subject(subject)
    return [_lesson_summary(lesson, subject) for lesson in lessons]


@router.get("/{subject}/{question_type}")
async def get_lesson(subject: str, question_type: str):
    """Get full lesson content for a specific question type."""
    if subject not in SUBJECT_FILES:
        raise HTTPException(status_code=404, detail=f"Unknown subject: {subject}")

    lessons = _load_subject(subject)
    for lesson in lessons:
        if lesson["questionType"] == question_type:
            return {**lesson, "subject": subject}

    raise HTTPException(
        status_code=404,
        detail=f"No lesson found for {subject}/{question_type}",
    )
