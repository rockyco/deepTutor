"""Question-related Pydantic models."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Subject(str, Enum):
    """11+ exam subjects."""

    ENGLISH = "english"
    MATHS = "maths"
    VERBAL_REASONING = "verbal_reasoning"
    NON_VERBAL_REASONING = "non_verbal_reasoning"


class QuestionType(str, Enum):
    """Question types across all subjects."""

    # English types
    COMPREHENSION = "comprehension"
    GRAMMAR = "grammar"
    SPELLING = "spelling"
    VOCABULARY = "vocabulary"
    SENTENCE_COMPLETION = "sentence_completion"
    PUNCTUATION = "punctuation"

    # Maths types
    NUMBER_OPERATIONS = "number_operations"
    FRACTIONS = "fractions"
    DECIMALS = "decimals"
    PERCENTAGES = "percentages"
    GEOMETRY = "geometry"
    MEASUREMENT = "measurement"
    DATA_HANDLING = "data_handling"
    WORD_PROBLEMS = "word_problems"
    ALGEBRA = "algebra"
    RATIO = "ratio"

    # Verbal Reasoning types (21 GL types)
    VR_INSERT_LETTER = "vr_insert_letter"
    VR_ODD_ONES_OUT = "vr_odd_ones_out"
    VR_ALPHABET_CODE = "vr_alphabet_code"
    VR_SYNONYMS = "vr_synonyms"
    VR_HIDDEN_WORD = "vr_hidden_word"
    VR_MISSING_WORD = "vr_missing_word"
    VR_NUMBER_SERIES = "vr_number_series"
    VR_LETTER_SERIES = "vr_letter_series"
    VR_NUMBER_CONNECTIONS = "vr_number_connections"
    VR_WORD_PAIRS = "vr_word_pairs"
    VR_MULTIPLE_MEANING = "vr_multiple_meaning"
    VR_LETTER_RELATIONSHIPS = "vr_letter_relationships"
    VR_NUMBER_CODES = "vr_number_codes"
    VR_COMPOUND_WORDS = "vr_compound_words"
    VR_WORD_SHUFFLING = "vr_word_shuffling"
    VR_ANAGRAMS = "vr_anagrams"
    VR_LOGIC_PROBLEMS = "vr_logic_problems"
    VR_EXPLORE_FACTS = "vr_explore_facts"
    VR_SOLVE_RIDDLE = "vr_solve_riddle"
    VR_RHYMING_SYNONYMS = "vr_rhyming_synonyms"
    VR_SHUFFLED_SENTENCES = "vr_shuffled_sentences"

    # Non-verbal Reasoning types
    NVR_SEQUENCES = "nvr_sequences"
    NVR_ODD_ONE_OUT = "nvr_odd_one_out"
    NVR_ANALOGIES = "nvr_analogies"
    NVR_MATRICES = "nvr_matrices"
    NVR_ROTATION = "nvr_rotation"
    NVR_REFLECTION = "nvr_reflection"
    NVR_SPATIAL_3D = "nvr_spatial_3d"
    NVR_CODES = "nvr_codes"
    NVR_VISUAL = "nvr_visual"


class QuestionFormat(str, Enum):
    """How the question is presented to the user."""

    MULTIPLE_CHOICE = "multiple_choice"
    FILL_IN_BLANK = "fill_in_blank"
    DRAG_DROP = "drag_drop"
    MATCHING = "matching"
    ORDERING = "ordering"
    FREE_TEXT = "free_text"


class Hint(BaseModel):
    """A progressive hint for a question."""

    level: int = Field(ge=1, le=3, description="Hint level (1=subtle, 3=detailed)")
    text: str
    penalty: float = Field(default=0.1, description="Score penalty for using this hint")


class QuestionContent(BaseModel):
    """The actual content of a question - varies by format."""

    text: str = Field(description="Main question text or prompt")
    passage: str | None = Field(default=None, description="For comprehension questions")
    options: list[str] | None = Field(default=None, description="For multiple choice")
    option_images: list[str] | None = Field(default=None, description="For visual options")
    image_url: str | None = Field(default=None, description="For visual questions")
    images: list[str] | None = Field(default=None, description="For NVR with multiple images")
    items: list[str] | None = Field(default=None, description="For drag-drop/ordering")
    pairs: dict[str, str] | None = Field(default=None, description="For matching questions")
    context: dict[str, Any] | None = Field(default=None, description="Additional context data")
    multi_select: bool = Field(default=False, description="Whether multiple options can be selected")


class Answer(BaseModel):
    """Correct answer(s) for a question."""

    value: str | list[str] | dict[str, str]
    accept_variations: list[str] | None = Field(
        default=None, description="Alternative accepted answers"
    )
    case_sensitive: bool = False
    order_matters: bool = True


class Question(BaseModel):
    """A complete question with all metadata."""

    id: UUID = Field(default_factory=uuid4)
    subject: Subject
    question_type: QuestionType
    format: QuestionFormat = QuestionFormat.MULTIPLE_CHOICE
    difficulty: int = Field(ge=1, le=5, default=3)
    content: QuestionContent
    answer: Answer
    explanation: str = Field(description="Detailed explanation of the answer")
    hints: list[Hint] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "subject": "verbal_reasoning",
                "question_type": "vr_synonyms",
                "format": "multiple_choice",
                "difficulty": 2,
                "content": {
                    "text": "Find two words, one from each group, that are closest in meaning.\n(happy sad angry) (joyful tired hungry)",
                    "options": ["happy, joyful", "sad, tired", "angry, hungry", "happy, tired"],
                },
                "answer": {"value": "happy, joyful"},
                "explanation": "'Happy' and 'joyful' both mean feeling pleasure or delight. They are synonyms.",
                "hints": [
                    {"level": 1, "text": "Look for words that describe similar emotions.", "penalty": 0.1}
                ],
            }
        }


class QuestionCreate(BaseModel):
    """Model for creating a new question."""

    subject: Subject
    question_type: QuestionType
    format: QuestionFormat = QuestionFormat.MULTIPLE_CHOICE
    difficulty: int = Field(ge=1, le=5, default=3)
    content: QuestionContent
    answer: Answer
    explanation: str
    hints: list[Hint] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source: str | None = None


class AnswerCheck(BaseModel):
    """User's answer submission for checking."""

    question_id: UUID
    user_answer: str | list[str] | dict[str, str]
    time_taken_seconds: int | None = None
    hints_used: int = 0


class AnswerResult(BaseModel):
    """Result of checking a user's answer."""

    is_correct: bool
    correct_answer: str | list[str] | dict[str, str]
    explanation: str
    score: float = Field(description="Score considering hints and time")
    feedback: str = Field(description="Personalized feedback message")
