"""Validation and deduplication for crawled questions."""

import hashlib
import logging
import re
from typing import Any

from rapidfuzz import fuzz

from app.models.question import QuestionFormat, QuestionType, Subject

logger = logging.getLogger(__name__)


class QuestionValidator:
    """Validates and deduplicates crawled questions."""

    # Minimum requirements for a valid question
    MIN_QUESTION_LENGTH = 10
    MIN_OPTIONS = 2
    MAX_OPTIONS = 6
    MIN_OPTION_LENGTH = 1

    def __init__(self):
        """Initialize validator with empty duplicate tracking."""
        self._seen_hashes: set[str] = set()

    def reset(self) -> None:
        """Reset duplicate tracking state."""
        self._seen_hashes.clear()

    def validate_questions(
        self, questions: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Validate a list of questions.

        Args:
            questions: List of question dicts in app format

        Returns:
            Tuple of (valid_questions, invalid_questions)
        """
        valid = []
        invalid = []

        for q in questions:
            errors = self.validate_question(q)
            if errors:
                q["_validation_errors"] = errors
                invalid.append(q)
            else:
                valid.append(q)

        logger.info(f"Validated {len(questions)} questions: {len(valid)} valid, {len(invalid)} invalid")
        return valid, invalid

    def validate_question(self, question: dict[str, Any]) -> list[str]:
        """Validate a single question.

        Args:
            question: Question dict in app format

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check required fields
        required = ["subject", "question_type", "content", "answer", "explanation"]
        for field in required:
            if field not in question:
                errors.append(f"Missing required field: {field}")

        if errors:
            return errors  # Can't continue without required fields

        # Validate subject
        try:
            Subject(question["subject"])
        except ValueError:
            errors.append(f"Invalid subject: {question['subject']}")

        # Validate question type
        try:
            QuestionType(question["question_type"])
        except ValueError:
            errors.append(f"Invalid question_type: {question['question_type']}")

        # Validate format if present
        if "format" in question:
            try:
                QuestionFormat(question["format"])
            except ValueError:
                errors.append(f"Invalid format: {question['format']}")

        # Validate content
        content = question.get("content", {})
        if not isinstance(content, dict):
            errors.append("Content must be a dictionary")
        else:
            text = content.get("text", "")
            if len(text) < self.MIN_QUESTION_LENGTH:
                errors.append(f"Question text too short: {len(text)} chars")

            # Only validate options for multiple_choice format
            q_format = question.get("format", "multiple_choice")
            if q_format == "multiple_choice":
                options = content.get("options", [])
                if isinstance(options, list):
                    if len(options) < self.MIN_OPTIONS:
                        errors.append(f"Too few options: {len(options)}")
                    elif len(options) > self.MAX_OPTIONS:
                        errors.append(f"Too many options: {len(options)}")

                    for i, opt in enumerate(options):
                        if len(str(opt)) < self.MIN_OPTION_LENGTH:
                            errors.append(f"Option {i+1} is empty")

        # Validate answer
        answer = question.get("answer", {})
        if not isinstance(answer, dict):
            errors.append("Answer must be a dictionary")
        elif "value" not in answer:
            errors.append("Answer missing 'value' field")
        elif not answer["value"]:
            errors.append("Answer value is empty")

        # Validate difficulty if present
        difficulty = question.get("difficulty")
        if difficulty is not None:
            if not isinstance(difficulty, int) or difficulty < 1 or difficulty > 5:
                errors.append(f"Invalid difficulty: {difficulty} (must be 1-5)")

        # Validate hints if present
        hints = question.get("hints", [])
        if hints:
            for i, hint in enumerate(hints):
                if not isinstance(hint, dict):
                    errors.append(f"Hint {i+1} is not a dictionary")
                elif "level" not in hint or "text" not in hint:
                    errors.append(f"Hint {i+1} missing level or text")

        return errors

    def deduplicate(
        self, questions: list[dict[str, Any]], include_existing: bool = True
    ) -> tuple[list[dict[str, Any]], int]:
        """Remove duplicate questions.

        Args:
            questions: List of question dicts
            include_existing: If True, also checks against previously seen questions

        Returns:
            Tuple of (unique_questions, num_duplicates_removed)
        """
        if not include_existing:
            self._seen_hashes.clear()

        unique = []
        duplicates = 0

        for q in questions:
            q_hash = self._question_hash(q)
            if q_hash in self._seen_hashes:
                duplicates += 1
                logger.debug(f"Duplicate found: {q.get('content', {}).get('text', '')[:50]}...")
            else:
                self._seen_hashes.add(q_hash)
                unique.append(q)

        logger.info(f"Deduplication: {len(questions)} -> {len(unique)} ({duplicates} duplicates)")
        return unique, duplicates

    def _question_hash(self, question: dict[str, Any]) -> str:
        """Generate a hash for a question based on content.

        Uses normalized question text and options to detect semantic duplicates.
        """
        content = question.get("content", {})

        # Normalize question text
        text = self._normalize_text(content.get("text", ""))

        # Normalize and sort options for order-independent comparison
        options = content.get("options", [])
        normalized_options = sorted(self._normalize_text(str(opt)) for opt in options)

        # Combine for hash
        hash_input = f"{text}|{'|'.join(normalized_options)}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison.

        - Lowercase
        - Remove extra whitespace
        - Remove punctuation (except essential)
        """
        text = text.lower()
        text = " ".join(text.split())  # Normalize whitespace
        text = re.sub(r"[^\w\s\?\.\,]", "", text)  # Keep basic punctuation
        return text.strip()

    def filter_by_quality(
        self, questions: list[dict[str, Any]], min_explanation_length: int = 20
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Filter questions by quality criteria.

        Args:
            questions: List of question dicts
            min_explanation_length: Minimum characters for explanation

        Returns:
            Tuple of (high_quality, low_quality)
        """
        high_quality = []
        low_quality = []

        for q in questions:
            is_high_quality = True

            # Check explanation length
            explanation = q.get("explanation", "")
            if len(explanation) < min_explanation_length:
                is_high_quality = False

            # Check if answer is in options
            answer = q.get("answer", {}).get("value", "")
            options = q.get("content", {}).get("options", [])
            if answer and options and answer not in options:
                is_high_quality = False

            # Check for placeholder text
            text = q.get("content", {}).get("text", "")
            placeholders = ["example", "placeholder", "todo", "fixme", "xxx"]
            if any(p in text.lower() for p in placeholders):
                is_high_quality = False

            if is_high_quality:
                high_quality.append(q)
            else:
                low_quality.append(q)

        logger.info(
            f"Quality filter: {len(questions)} -> {len(high_quality)} high quality, "
            f"{len(low_quality)} low quality"
        )
        return high_quality, low_quality

    def fuzzy_deduplicate(
        self,
        questions: list[dict[str, Any]],
        similarity_threshold: float = 85.0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Remove near-duplicate questions using fuzzy matching.

        More aggressive than hash-based deduplication - catches questions
        that are semantically similar but have minor text differences.

        Args:
            questions: List of question dicts
            similarity_threshold: Minimum similarity score (0-100) to consider duplicates

        Returns:
            Tuple of (unique_questions, num_duplicates_removed)
        """
        unique = []
        duplicates = 0
        seen_texts: list[str] = []

        for q in questions:
            q_text = self._get_question_text(q)
            if not q_text:
                unique.append(q)
                continue

            # Check against all seen questions
            is_duplicate = False
            for seen_text in seen_texts:
                similarity = fuzz.ratio(q_text, seen_text)
                if similarity >= similarity_threshold:
                    is_duplicate = True
                    duplicates += 1
                    logger.debug(
                        f"Fuzzy duplicate ({similarity:.0f}%): "
                        f"{q_text[:50]}... ~ {seen_text[:50]}..."
                    )
                    break

            if not is_duplicate:
                unique.append(q)
                seen_texts.append(q_text)

        logger.info(
            f"Fuzzy deduplication: {len(questions)} -> {len(unique)} "
            f"({duplicates} duplicates at {similarity_threshold}% threshold)"
        )
        return unique, duplicates

    def _get_question_text(self, question: dict[str, Any]) -> str:
        """Extract normalized question text for comparison."""
        content = question.get("content", {})
        text = content.get("text", "")
        return self._normalize_text(text)

    def deduplicate_against_existing(
        self,
        new_questions: list[dict[str, Any]],
        existing_questions: list[dict[str, Any]],
        use_fuzzy: bool = True,
        similarity_threshold: float = 85.0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Remove questions that already exist in the database.

        Args:
            new_questions: Newly crawled questions
            existing_questions: Questions already in database
            use_fuzzy: Whether to use fuzzy matching
            similarity_threshold: Similarity threshold for fuzzy matching

        Returns:
            Tuple of (novel_questions, num_duplicates)
        """
        # Build lookup for existing questions
        existing_hashes = set()
        existing_texts = []

        for q in existing_questions:
            existing_hashes.add(self._question_hash(q))
            if use_fuzzy:
                existing_texts.append(self._get_question_text(q))

        novel = []
        duplicates = 0

        for q in new_questions:
            # Check hash first (fast)
            q_hash = self._question_hash(q)
            if q_hash in existing_hashes:
                duplicates += 1
                continue

            # Check fuzzy match if enabled
            if use_fuzzy:
                q_text = self._get_question_text(q)
                is_duplicate = False

                for existing_text in existing_texts:
                    if fuzz.ratio(q_text, existing_text) >= similarity_threshold:
                        is_duplicate = True
                        duplicates += 1
                        break

                if is_duplicate:
                    continue

            novel.append(q)

        logger.info(
            f"Deduplicated against existing: {len(new_questions)} -> {len(novel)} "
            f"({duplicates} duplicates)"
        )
        return novel, duplicates

    def categorize_by_confidence(
        self, questions: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Categorize questions by answer confidence.

        Returns dict with 'high', 'medium', 'low' confidence buckets.
        """
        high = []
        medium = []
        low = []

        for q in questions:
            confidence = self._assess_answer_confidence(q)

            if confidence >= 0.8:
                high.append(q)
            elif confidence >= 0.5:
                medium.append(q)
            else:
                low.append(q)

        return {
            "high": high,
            "medium": medium,
            "low": low,
        }

    def _assess_answer_confidence(self, question: dict[str, Any]) -> float:
        """Assess confidence in the question's answer.

        Returns a score from 0 to 1.
        """
        confidence = 0.5  # Default medium

        answer = question.get("answer", {}).get("value", "")
        options = question.get("content", {}).get("options", [])
        explanation = question.get("explanation", "")

        # Answer is in options: higher confidence
        if answer and options and answer in options:
            confidence += 0.2

        # Has meaningful explanation: higher confidence
        if explanation and len(explanation) > 30:
            confidence += 0.2

        # Answer references correct answer: higher confidence
        if explanation and answer and answer.lower() in explanation.lower():
            confidence += 0.1

        return min(1.0, confidence)
