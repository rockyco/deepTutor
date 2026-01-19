"""Convert raw crawled questions to app JSON format."""

import logging
import re
from typing import Any

from app.models.question import QuestionType, Subject

from .models import CrawlResult, RawQuestion

logger = logging.getLogger(__name__)


class QuestionConverter:
    """Converts RawQuestion objects to app's question JSON format."""

    # Default question types when category mapping fails
    DEFAULT_TYPES = {
        "verbal_reasoning": QuestionType.VR_LOGIC_PROBLEMS,
        "non_verbal_reasoning": QuestionType.NVR_SEQUENCES,
        "maths": QuestionType.WORD_PROBLEMS,
        "english": QuestionType.COMPREHENSION,
    }

    # Subject string to enum mapping
    SUBJECT_MAP = {
        "verbal_reasoning": Subject.VERBAL_REASONING,
        "non_verbal_reasoning": Subject.NON_VERBAL_REASONING,
        "maths": Subject.MATHS,
        "english": Subject.ENGLISH,
    }

    def __init__(self, source_name: str = "crawled"):
        """Initialize converter.

        Args:
            source_name: Source identifier for converted questions
        """
        self.source_name = source_name

    def convert_result(self, result: CrawlResult) -> dict[str, Any]:
        """Convert a CrawlResult to app JSON format.

        Returns a dict with 'questions' key containing list of question dicts.
        """
        questions = []

        for raw_q in result.questions:
            try:
                converted = self.convert_question(raw_q, result.subject)
                if converted:
                    questions.append(converted)
            except Exception as e:
                logger.warning(f"Failed to convert question: {e}")

        return {
            "metadata": {
                "source": result.source,
                "subject": result.subject,
                "total_crawled": len(result.questions),
                "total_converted": len(questions),
                "crawl_duration_seconds": result.duration_seconds,
            },
            "questions": questions,
        }

    def convert_question(
        self, raw: RawQuestion, subject: str
    ) -> dict[str, Any] | None:
        """Convert a single RawQuestion to app JSON format.

        Args:
            raw: The raw question from crawler
            subject: Subject string (e.g., 'verbal_reasoning')

        Returns:
            Question dict matching app's QuestionCreate schema, or None if invalid
        """
        # Validate minimum requirements
        if not raw.question_text or len(raw.options) < 2:
            return None

        # Get subject enum
        subject_enum = self.SUBJECT_MAP.get(subject)
        if not subject_enum:
            logger.warning(f"Unknown subject: {subject}")
            return None

        # Determine question type
        question_type = self._determine_question_type(raw, subject)

        # Determine difficulty
        difficulty = self._estimate_difficulty(raw)

        # Build content - filter out bad options first
        clean_options = self._filter_valid_options(raw.options)
        if len(clean_options) < 2:
            # Fall back to original if filter removes too many
            clean_options = raw.options[:4]

        content = {
            "text": self._clean_text(raw.question_text),
            "options": [self._clean_text(opt) for opt in clean_options[:4]],
        }

        # Add images if present
        if raw.image_urls:
            if len(raw.image_urls) == 1:
                content["image_url"] = raw.image_urls[0]
            else:
                content["images"] = raw.image_urls

        # Build answer
        correct = self._find_correct_answer(raw)
        answer = {
            "value": correct,
            "case_sensitive": False,
        }

        # Build explanation
        explanation = raw.explanation or self._generate_basic_explanation(raw, correct)

        # Build hints
        hints = self._generate_hints(raw, subject)

        # Build tags
        tags = self._generate_tags(raw, subject)

        return {
            "subject": subject_enum.value,
            "question_type": question_type.value,
            "format": "multiple_choice",
            "difficulty": difficulty,
            "content": content,
            "answer": answer,
            "explanation": explanation,
            "hints": hints,
            "tags": tags,
            "source": f"{self.source_name}:{raw.source_url}",
        }

    def _determine_question_type(
        self, raw: RawQuestion, subject: str
    ) -> QuestionType:
        """Determine question type from raw data and subject."""
        # Try to use source category if it's a valid QuestionType
        if raw.source_category:
            try:
                return QuestionType(raw.source_category)
            except ValueError:
                pass

        # Analyze question text for type hints
        text_lower = raw.question_text.lower()

        if subject == "verbal_reasoning":
            return self._detect_vr_type(text_lower)
        elif subject == "non_verbal_reasoning":
            return self._detect_nvr_type(text_lower)
        elif subject == "maths":
            return self._detect_maths_type(text_lower)
        elif subject == "english":
            return self._detect_english_type(text_lower)

        return self.DEFAULT_TYPES.get(subject, QuestionType.WORD_PROBLEMS)

    def _detect_vr_type(self, text: str) -> QuestionType:
        """Detect verbal reasoning question type from text."""
        if any(w in text for w in ["synonym", "closest in meaning", "similar meaning"]):
            return QuestionType.VR_SYNONYMS
        elif any(w in text for w in ["hidden word", "hidden in"]):
            return QuestionType.VR_HIDDEN_WORD
        elif any(w in text for w in ["odd one", "different from the others"]):
            return QuestionType.VR_ODD_ONES_OUT
        elif any(w in text for w in ["complete the series", "number series", "next number"]):
            return QuestionType.VR_NUMBER_SERIES
        elif any(w in text for w in ["letter series", "next letter"]):
            return QuestionType.VR_LETTER_SERIES
        elif any(w in text for w in ["code", "coded"]):
            return QuestionType.VR_ALPHABET_CODE
        elif any(w in text for w in ["compound word"]):
            return QuestionType.VR_COMPOUND_WORDS
        elif any(w in text for w in ["anagram", "rearrange"]):
            return QuestionType.VR_ANAGRAMS
        elif any(w in text for w in ["missing letter"]):
            return QuestionType.VR_INSERT_LETTER
        elif any(w in text for w in ["word pair", "word connection", "related"]):
            return QuestionType.VR_WORD_PAIRS
        return QuestionType.VR_LOGIC_PROBLEMS

    def _detect_nvr_type(self, text: str) -> QuestionType:
        """Detect non-verbal reasoning question type from text."""
        if any(w in text for w in ["sequence", "pattern", "next in"]):
            return QuestionType.NVR_SEQUENCES
        elif any(w in text for w in ["odd one", "different"]):
            return QuestionType.NVR_ODD_ONE_OUT
        elif any(w in text for w in ["analogy", "is to"]):
            return QuestionType.NVR_ANALOGIES
        elif any(w in text for w in ["matrix", "matrices"]):
            return QuestionType.NVR_MATRICES
        elif any(w in text for w in ["rotation", "rotate"]):
            return QuestionType.NVR_ROTATION
        elif any(w in text for w in ["reflection", "mirror"]):
            return QuestionType.NVR_REFLECTION
        elif any(w in text for w in ["3d", "cube", "fold", "net"]):
            return QuestionType.NVR_SPATIAL_3D
        return QuestionType.NVR_SEQUENCES

    def _detect_maths_type(self, text: str) -> QuestionType:
        """Detect maths question type from text."""
        if any(w in text for w in ["fraction"]):
            return QuestionType.FRACTIONS
        elif any(w in text for w in ["decimal"]):
            return QuestionType.DECIMALS
        elif any(w in text for w in ["percent", "%"]):
            return QuestionType.PERCENTAGES
        elif any(w in text for w in ["angle", "triangle", "square", "rectangle", "circle", "shape"]):
            return QuestionType.GEOMETRY
        elif any(w in text for w in ["measure", "length", "weight", "volume", "time"]):
            return QuestionType.MEASUREMENT
        elif any(w in text for w in ["graph", "chart", "data", "table"]):
            return QuestionType.DATA_HANDLING
        elif any(w in text for w in ["ratio"]):
            return QuestionType.RATIO
        elif any(w in text for w in ["algebra", "x =", "solve for"]):
            return QuestionType.ALGEBRA
        elif any(w in text for w in ["+", "-", "*", "/", "add", "subtract", "multiply", "divide"]):
            return QuestionType.NUMBER_OPERATIONS
        return QuestionType.WORD_PROBLEMS

    def _detect_english_type(self, text: str) -> QuestionType:
        """Detect English question type from text."""
        if any(w in text for w in ["passage", "read the", "according to"]):
            return QuestionType.COMPREHENSION
        elif any(w in text for w in ["grammar", "correct sentence", "verb", "noun"]):
            return QuestionType.GRAMMAR
        elif any(w in text for w in ["spell", "spelling"]):
            return QuestionType.SPELLING
        elif any(w in text for w in ["vocabulary", "meaning of", "means"]):
            return QuestionType.VOCABULARY
        elif any(w in text for w in ["complete", "fill in", "blank"]):
            return QuestionType.SENTENCE_COMPLETION
        return QuestionType.COMPREHENSION

    def _estimate_difficulty(self, raw: RawQuestion) -> int:
        """Estimate difficulty on 1-5 scale based on question characteristics."""
        difficulty = 3  # Default medium

        text = raw.question_text

        # Longer questions tend to be harder
        word_count = len(text.split())
        if word_count > 50:
            difficulty += 1
        elif word_count < 15:
            difficulty -= 1

        # More options can indicate harder questions
        if len(raw.options) >= 5:
            difficulty += 1

        # Check for complexity indicators
        complexity_indicators = [
            "therefore", "however", "although", "consequently",
            "calculate", "determine", "analyze", "evaluate",
            "which of the following", "all of the above"
        ]
        if any(ind in text.lower() for ind in complexity_indicators):
            difficulty += 1

        # Clamp to 1-5 range
        return max(1, min(5, difficulty))

    def _find_correct_answer(self, raw: RawQuestion) -> str:
        """Find the correct answer, defaulting to first option if unknown."""
        # Get filtered options for matching
        filtered_options = self._filter_valid_options(raw.options)
        if len(filtered_options) < 2:
            filtered_options = raw.options

        if raw.correct_answer:
            # Clean up the answer
            clean = self._clean_text(raw.correct_answer)
            # Remove option letter prefix if present
            clean = re.sub(r"^[A-Da-d][\.\)]\s*", "", clean)

            # Check if the answer looks like concatenated garbage
            if not self._is_valid_answer(clean, filtered_options):
                # Try to extract from explanation
                extracted = self._extract_answer_from_explanation(raw.explanation, filtered_options)
                if extracted:
                    return extracted
                # Fall back to first valid option
                if filtered_options:
                    return self._clean_text(filtered_options[0])

            return clean

        # Try to extract from explanation first
        if raw.explanation:
            extracted = self._extract_answer_from_explanation(raw.explanation, filtered_options)
            if extracted:
                return extracted

        # Default to first option (will need manual verification)
        if filtered_options:
            return self._clean_text(filtered_options[0])

        return ""

    def _filter_valid_options(self, options: list[str]) -> list[str]:
        """Filter out invalid options like concatenated text.

        Detects when one option contains all others (common parsing artifact).
        """
        if len(options) < 2:
            return options

        valid_options = []

        for i, opt in enumerate(options):
            # Skip if this option contains multiple other options (concatenated)
            if self._is_concatenated_option(opt, options, i):
                continue

            # Skip overly long options without spaces (likely concatenated)
            if len(opt) > 20 and " " not in opt:
                continue

            valid_options.append(opt)

        return valid_options if len(valid_options) >= 2 else options

    def _is_concatenated_option(
        self, opt: str, all_options: list[str], opt_index: int
    ) -> bool:
        """Check if an option is a concatenation of other options."""
        opt_upper = opt.upper()

        # Count how many other options appear within this option
        contained_count = 0
        for i, other in enumerate(all_options):
            if i == opt_index:
                continue
            if len(other) > 2 and other.upper() in opt_upper:
                contained_count += 1

        # If this option contains 2+ other options, it's concatenated
        return contained_count >= 2

    def _is_valid_answer(self, answer: str, options: list[str]) -> bool:
        """Check if an answer looks valid.

        Filters out concatenated garbage like "BRIDSBIRDSDRIBSSRIBD".
        """
        if not answer:
            return False

        # If answer is in options, it's valid
        for opt in options:
            if answer.lower() == opt.lower():
                return True

        # Check for concatenated text (long, no spaces, all same case)
        if len(answer) > 15 and " " not in answer:
            return False

        # Check if answer looks like multiple words concatenated
        if answer.isupper() and len(answer) > 10:
            # Count how many options appear in the answer
            matches = sum(1 for opt in options if opt.upper() in answer.upper())
            if matches > 1:
                return False

        return True

    def _extract_answer_from_explanation(
        self, explanation: str, options: list[str]
    ) -> str:
        """Extract the correct answer from explanation text."""
        if not explanation or not options:
            return ""

        explanation_lower = explanation.lower()

        # Patterns that indicate the answer
        patterns = [
            r"(?:the\s+)?answer\s+(?:is|must\s+be|should\s+be)\s+['\"]?(\w+)['\"]?",
            r"(?:so\s+)?['\"]?(\w+)['\"]?\s+is\s+(?:the\s+)?(?:correct|right)",
            r"correct\s+answer\s+is\s+['\"]?(\w+)['\"]?",
        ]

        for pattern in patterns:
            match = re.search(pattern, explanation_lower)
            if match:
                answer_word = match.group(1)
                # Find matching option (case-insensitive)
                for opt in options:
                    opt_clean = self._clean_text(opt)
                    if opt_clean.lower() == answer_word.lower():
                        return opt_clean
                    if answer_word.lower() in opt_clean.lower():
                        return opt_clean

        # Direct option mention check
        for opt in options:
            opt_clean = self._clean_text(opt).lower()
            if f"answer is {opt_clean}" in explanation_lower:
                return opt
            if f"answer must be {opt_clean}" in explanation_lower:
                return opt

        return ""

    def _generate_basic_explanation(
        self, raw: RawQuestion, correct: str
    ) -> str:
        """Generate a basic explanation when none is provided."""
        return f"The correct answer is '{correct}'."

    def _generate_hints(
        self, raw: RawQuestion, subject: str
    ) -> list[dict[str, Any]]:
        """Generate basic hints based on question content."""
        hints = []

        # Level 1: General guidance
        if subject == "verbal_reasoning":
            hints.append({
                "level": 1,
                "text": "Read the question carefully and look for patterns or relationships.",
                "penalty": 0.1
            })
        elif subject == "non_verbal_reasoning":
            hints.append({
                "level": 1,
                "text": "Look at shapes, patterns, and how they change.",
                "penalty": 0.1
            })
        elif subject == "maths":
            hints.append({
                "level": 1,
                "text": "Identify what operation or concept is being tested.",
                "penalty": 0.1
            })
        elif subject == "english":
            hints.append({
                "level": 1,
                "text": "Read the text carefully before looking at the options.",
                "penalty": 0.1
            })

        # Level 2: More specific (based on number of options)
        if raw.options and len(raw.options) >= 3:
            hints.append({
                "level": 2,
                "text": "Try eliminating options that are clearly wrong.",
                "penalty": 0.2
            })

        return hints

    def _generate_tags(self, raw: RawQuestion, subject: str) -> list[str]:
        """Generate tags based on question content and source."""
        tags = [subject.replace("_", "-")]

        if raw.source_category:
            tags.append(raw.source_category.replace("_", "-"))

        # Add source tag
        if raw.source_name:
            tags.append(f"source:{raw.source_name.replace(' ', '-')}")

        return tags

    def _clean_text(self, text: str) -> str:
        """Clean up text by normalizing whitespace and removing artifacts."""
        if not text:
            return ""

        # Normalize whitespace
        text = " ".join(text.split())

        # Remove common artifacts
        text = text.strip()

        return text
