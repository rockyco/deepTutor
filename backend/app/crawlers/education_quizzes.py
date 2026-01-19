"""Crawler for educationquizzes.com 11+ content."""

import logging
import re
from urllib.parse import urljoin

from .base import BaseCrawler
from .models import RawQuestion

logger = logging.getLogger(__name__)


class EducationQuizzesCrawler(BaseCrawler):
    """Crawler for educationquizzes.com.

    Site structure:
    - Subject listing: /11-plus/[subject].php
    - Individual quiz: /11-plus/[subject]/[quiz-name].php
    - Each quiz has 10 questions with 4 options and explanations
    """

    BASE_URL = "https://www.educationquizzes.com"
    SOURCE_NAME = "educationquizzes.com"
    REQUEST_DELAY = 2.0  # Be polite

    # Map our subject names to their URL paths
    SUBJECT_PATHS = {
        "verbal_reasoning": "11-plus/verbal-reasoning",
        "non_verbal_reasoning": "11-plus/non-verbal-reasoning",
        "maths": "11-plus/maths",
        "english": "11-plus/english",
    }

    # Subcategory patterns for better classification
    CATEGORY_PATTERNS = {
        # Verbal Reasoning
        "synonyms": "vr_synonyms",
        "antonyms": "vr_synonyms",  # Similar skill
        "closest meaning": "vr_synonyms",
        "odd one out": "vr_odd_ones_out",
        "odd ones out": "vr_odd_ones_out",
        "hidden word": "vr_hidden_word",
        "missing letters": "vr_insert_letter",
        "insert a letter": "vr_insert_letter",
        "complete the word": "vr_insert_letter",
        "letter series": "vr_letter_series",
        "letter connections": "vr_letter_relationships",
        "number series": "vr_number_series",
        "number connections": "vr_number_connections",
        "complete the sum": "vr_number_connections",
        "codes": "vr_alphabet_code",
        "word connections": "vr_word_pairs",
        "word pairs": "vr_word_pairs",
        "compound words": "vr_compound_words",
        "make a word": "vr_compound_words",
        "anagram": "vr_anagrams",
        "shuffled": "vr_word_shuffling",
        "rearrange": "vr_anagrams",
        "logic": "vr_logic_problems",
        "reasoning": "vr_logic_problems",
        "multiple meaning": "vr_multiple_meaning",
        # Non-Verbal Reasoning
        "sequences": "nvr_sequences",
        "series": "nvr_sequences",
        "pattern": "nvr_sequences",
        "analogies": "nvr_analogies",
        "analogy": "nvr_analogies",
        "odd one": "nvr_odd_one_out",
        "matrices": "nvr_matrices",
        "matrix": "nvr_matrices",
        "reflection": "nvr_reflection",
        "mirror": "nvr_reflection",
        "rotation": "nvr_rotation",
        "rotate": "nvr_rotation",
        "3d": "nvr_spatial_3d",
        "cube": "nvr_spatial_3d",
        "fold": "nvr_spatial_3d",
        "net": "nvr_spatial_3d",
        "spatial": "nvr_spatial_3d",
        # Maths
        "addition": "number_operations",
        "subtraction": "number_operations",
        "multiplication": "number_operations",
        "division": "number_operations",
        "times table": "number_operations",
        "fractions": "fractions",
        "decimals": "decimals",
        "percentages": "percentages",
        "percent": "percentages",
        "geometry": "geometry",
        "shapes": "geometry",
        "angles": "geometry",
        "area": "geometry",
        "perimeter": "geometry",
        "measurement": "measurement",
        "time": "measurement",
        "length": "measurement",
        "weight": "measurement",
        "data": "data_handling",
        "graph": "data_handling",
        "chart": "data_handling",
        "algebra": "algebra",
        "equation": "algebra",
        "ratio": "ratio",
        "proportion": "ratio",
        "word problem": "word_problems",
        "problem solving": "word_problems",
        # English
        "comprehension": "comprehension",
        "reading": "comprehension",
        "passage": "comprehension",
        "grammar": "grammar",
        "tense": "grammar",
        "verb": "grammar",
        "spelling": "spelling",
        "spell": "spelling",
        "vocabulary": "vocabulary",
        "meaning": "vocabulary",
        "definition": "vocabulary",
        "punctuation": "grammar",
        "sentence": "sentence_completion",
        "cloze": "sentence_completion",
    }

    async def get_quiz_urls(self, subject: str) -> list[str]:
        """Get all quiz URLs for a subject from the listing page."""
        if subject not in self.SUBJECT_PATHS:
            raise ValueError(f"Unknown subject: {subject}")

        path = self.SUBJECT_PATHS[subject]
        listing_url = f"{self.BASE_URL}/{path}/"

        logger.info(f"Fetching quiz listing from {listing_url}")
        html = await self.fetch(listing_url)
        if not html:
            return []

        soup = self.parse_html(html)
        quiz_urls = []

        # Find links to individual quizzes
        # Pattern: /11-plus/[subject]/[quiz-name] or /11-plus/[subject]/[quiz-name].php
        quiz_pattern = re.compile(
            rf"/{re.escape(path)}/[a-z0-9_-]+(?:\.php)?/?$",
            re.IGNORECASE
        )

        for link in soup.find_all("a", href=True):
            href = link["href"]
            # Skip if it's just the listing page itself
            if href.rstrip("/") == f"/{path}" or href == f"/{path}/":
                continue
            if quiz_pattern.search(href):
                full_url = urljoin(self.BASE_URL, href)
                if full_url not in quiz_urls:
                    quiz_urls.append(full_url)

        logger.info(f"Found {len(quiz_urls)} quiz URLs for {subject}")
        return quiz_urls

    async def parse_quiz(self, url: str, html: str) -> list[RawQuestion]:
        """Extract questions from a quiz page.

        Education Quizzes format:
        - Questions in div.question or similar elements
        - Options typically labeled A, B, C, D
        - Correct answer shown after submission
        - Explanation provided for each question
        """
        soup = self.parse_html(html)
        questions = []

        # Extract category from URL
        category = self._extract_category_from_url(url)

        # Try multiple parsing strategies in order of reliability
        # Strategy 1: Parse from page body text (numbered questions)
        questions = self._parse_from_body_text(soup, category, url)

        # Strategy 2: Try div-based containers
        if not questions:
            questions = self._parse_question_divs(soup, category, url)

        # Strategy 3: Try structured text elements
        if not questions:
            questions = self._parse_structured_questions(soup, category, url)

        if not questions:
            logger.warning(f"Could not extract questions from {url}")

        return questions

    def _parse_from_body_text(
        self, soup, category: str, url: str
    ) -> list[RawQuestion]:
        """Parse questions from page body text.

        This handles pages where questions are embedded as plain text
        with numbered format like "1 . Question text here"
        """
        questions = []

        # Get main content area - try common content containers
        content = None
        for selector in ["main", "article", ".content", "#content", ".quiz-content", "body"]:
            content = soup.select_one(selector)
            if content:
                break

        if not content:
            return []

        # Get full text and look for numbered questions
        text = content.get_text(separator="\n")

        # Pattern for numbered questions: "1 ." or "1." or "1)" at start of line
        question_pattern = re.compile(
            r"^\s*(\d{1,2})\s*[\.\)]\s*(.+?)$",
            re.MULTILINE
        )

        # Find all question starts
        matches = list(question_pattern.finditer(text))

        for i, match in enumerate(matches):
            q_num = int(match.group(1))
            q_start = match.end()

            # Get text until next question or end
            if i + 1 < len(matches):
                q_end = matches[i + 1].start()
            else:
                q_end = len(text)

            question_block = text[match.start():q_end]

            # Try to extract question and options
            q = self._parse_question_block(question_block, category, q_num)
            if q:
                questions.append(q)

        return questions

    def _parse_question_block(
        self, block: str, category: str, q_num: int
    ) -> RawQuestion | None:
        """Parse a single question block containing question text and options."""
        lines = [l.strip() for l in block.split("\n") if l.strip()]

        if len(lines) < 3:  # Need at least question + 2 options
            return None

        # First line contains question number and text
        first_line = lines[0]
        question_text = re.sub(r"^\s*\d{1,2}\s*[\.\)]\s*", "", first_line)

        if len(question_text) < 5:
            return None

        # Look for options - they might be on separate lines or labeled A, B, C, D
        options = []
        correct_answer = ""
        explanation = ""
        in_explanation = False

        for line in lines[1:]:
            # Skip empty lines
            if not line:
                continue

            # Check if this is an explanation marker
            if re.match(r"^(The correct answer|Answer|Explanation|The answer)\s*[:\-]?", line, re.I):
                in_explanation = True
                # Extract correct answer if present
                ans_match = re.search(r"correct answer[:\s]+(.+?)(?:\.|$)", line, re.I)
                if ans_match:
                    correct_answer = ans_match.group(1).strip()
                continue

            if in_explanation:
                explanation += " " + line
                continue

            # Check for option patterns (a), A., a., etc.)
            opt_match = re.match(r"^[(\[]?([A-Da-d])[)\]\.:\s]+(.+)$", line)
            if opt_match:
                opt_text = opt_match.group(2).strip()
                if opt_text:
                    options.append(opt_text)
            # Also accept lines that look like standalone options - but be strict
            elif self._looks_like_option(line) and len(options) < 4:
                options.append(line)

        # Filter out bad options (concatenated text, etc.)
        options = self._filter_valid_options(options)

        # Need at least 2 options to be valid
        if len(options) < 2:
            return None

        # Limit to 4 options
        options = options[:4]

        # Try to extract correct answer from explanation if not found
        if not correct_answer and explanation:
            correct_answer = self._extract_answer_from_explanation(explanation, options)

        return RawQuestion(
            question_text=question_text,
            options=options,
            correct_answer=correct_answer or (options[0] if options else ""),
            explanation=explanation.strip(),
            source_category=category,
        )

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

        return valid_options

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
            if other.upper() in opt_upper:
                contained_count += 1

        # If this option contains 2+ other options, it's concatenated
        return contained_count >= 2

    def _looks_like_option(self, line: str) -> bool:
        """Check if a line looks like a valid standalone option.

        Filters out:
        - Concatenated text (no spaces, too long)
        - UI elements (hints, buttons)
        - Questions (ending with ?)
        """
        # Skip if too long or too short
        if len(line) > 50 or len(line) < 2:
            return False

        # Skip if ends with question mark
        if line.endswith("?"):
            return False

        # Skip UI elements
        skip_words = ["hint", "help", "click", "submit", "next", "previous", "score"]
        if any(skip in line.lower() for skip in skip_words):
            return False

        # Skip if it looks like concatenated text (long string without spaces)
        if len(line) > 10 and " " not in line:
            # Allow short single words as options
            return False

        # Skip if all uppercase and long (likely concatenated options)
        if line.isupper() and len(line) > 15:
            return False

        return True

    def _extract_answer_from_explanation(
        self, explanation: str, options: list[str]
    ) -> str:
        """Extract the correct answer from explanation text.

        Looks for patterns like:
        - "the answer is X"
        - "the answer must be X"
        - "the correct answer is X"
        - "so X is correct"
        """
        explanation_lower = explanation.lower()

        # Patterns that indicate the answer
        patterns = [
            r"(?:the\s+)?answer\s+(?:is|must\s+be|should\s+be)\s+['\"]?(\w+)['\"]?",
            r"(?:so\s+)?['\"]?(\w+)['\"]?\s+is\s+(?:the\s+)?(?:correct|right)\s+answer",
            r"correct\s+answer\s+is\s+['\"]?(\w+)['\"]?",
        ]

        for pattern in patterns:
            match = re.search(pattern, explanation_lower)
            if match:
                answer_word = match.group(1).upper()
                # Find matching option (case-insensitive)
                for opt in options:
                    if opt.upper() == answer_word or answer_word in opt.upper():
                        return opt

        # Also try to find option text directly mentioned in explanation
        for opt in options:
            # Check if option is mentioned as the answer
            opt_lower = opt.lower()
            if f"answer is {opt_lower}" in explanation_lower:
                return opt
            if f"answer must be {opt_lower}" in explanation_lower:
                return opt

        return ""

    def _parse_question_divs(
        self, soup, category: str, url: str
    ) -> list[RawQuestion]:
        """Parse questions from div-based layout."""
        questions = []

        # Common patterns for question containers
        question_containers = soup.find_all(
            "div", class_=re.compile(r"question|quiz-item|q-block", re.I)
        )

        if not question_containers:
            # Try finding by structure
            question_containers = soup.find_all(
                "div", attrs={"data-question": True}
            )

        for container in question_containers:
            try:
                q = self._extract_question_from_container(container, category)
                if q:
                    questions.append(q)
            except Exception as e:
                logger.debug(f"Failed to parse question container: {e}")

        return questions

    def _parse_structured_questions(
        self, soup, category: str, url: str
    ) -> list[RawQuestion]:
        """Parse questions from a more structured layout.

        Looks for numbered questions with option lists.
        """
        questions = []

        # Look for question text patterns
        text_elements = soup.find_all(
            ["p", "div", "span"],
            string=re.compile(r"^\s*(Question\s+)?\d+[\.\):]", re.I)
        )

        for elem in text_elements:
            try:
                q = self._extract_question_from_text_element(elem, category)
                if q:
                    questions.append(q)
            except Exception as e:
                logger.debug(f"Failed to parse text element: {e}")

        return questions

    def _extract_question_from_container(
        self, container, category: str
    ) -> RawQuestion | None:
        """Extract a question from a container element."""
        # Find question text
        q_text_elem = container.find(
            class_=re.compile(r"question-text|q-text|prompt", re.I)
        )
        if not q_text_elem:
            q_text_elem = container.find(["h3", "h4", "p"])

        if not q_text_elem:
            return None

        question_text = q_text_elem.get_text(strip=True)
        if len(question_text) < 10:  # Too short to be a real question
            return None

        # Find options
        options = []
        option_elements = container.find_all(
            class_=re.compile(r"option|answer|choice", re.I)
        )
        if not option_elements:
            option_elements = container.find_all("li")

        for opt in option_elements[:4]:  # Max 4 options
            text = opt.get_text(strip=True)
            # Clean up option labels (A., B., etc.)
            text = re.sub(r"^[A-Da-d][\.\)]\s*", "", text)
            if text:
                options.append(text)

        if len(options) < 2:  # Need at least 2 options
            return None

        # Find correct answer
        correct_elem = container.find(
            class_=re.compile(r"correct|right|answer", re.I)
        )
        correct_answer = ""
        if correct_elem:
            # Check for highlighted option
            if "correct" in correct_elem.get("class", []):
                correct_answer = correct_elem.get_text(strip=True)
            else:
                correct_answer = correct_elem.get_text(strip=True)

        if not correct_answer and options:
            # Try to find by data attribute
            for opt in option_elements:
                if opt.get("data-correct") == "true":
                    correct_answer = opt.get_text(strip=True)
                    break

        # Find explanation
        explanation = ""
        expl_elem = container.find(
            class_=re.compile(r"explanation|reason|help", re.I)
        )
        if expl_elem:
            explanation = expl_elem.get_text(strip=True)

        return RawQuestion(
            question_text=question_text,
            options=options,
            correct_answer=correct_answer or options[0],  # Default to first if unknown
            explanation=explanation,
            source_category=category,
        )

    def _extract_question_from_text_element(
        self, elem, category: str
    ) -> RawQuestion | None:
        """Extract question from a text element with nearby siblings."""
        question_text = elem.get_text(strip=True)

        # Clean up question number
        question_text = re.sub(r"^\s*(Question\s+)?\d+[\.\):]\s*", "", question_text)

        if len(question_text) < 10:
            return None

        # Look for option list in siblings
        options = []
        sibling = elem.find_next_sibling()

        while sibling and len(options) < 4:
            if sibling.name in ["ul", "ol"]:
                for li in sibling.find_all("li")[:4]:
                    text = li.get_text(strip=True)
                    text = re.sub(r"^[A-Da-d][\.\)]\s*", "", text)
                    if text:
                        options.append(text)
                break
            elif sibling.name in ["p", "div"]:
                text = sibling.get_text(strip=True)
                if re.match(r"^[A-Da-d][\.\)]\s*", text):
                    text = re.sub(r"^[A-Da-d][\.\)]\s*", "", text)
                    if text:
                        options.append(text)
            sibling = sibling.find_next_sibling()

        if len(options) < 2:
            return None

        return RawQuestion(
            question_text=question_text,
            options=options,
            correct_answer=options[0],  # Will need manual verification
            explanation="",
            source_category=category,
        )

    def _extract_category_from_url(self, url: str) -> str:
        """Extract category/subcategory from URL path."""
        # Extract the quiz name from URL
        # Handles both /path/quiz-name/ and /path/quiz-name.php
        match = re.search(r"/([^/]+?)(?:\.php)?/?$", url)
        if match:
            quiz_name = match.group(1).replace("-", " ").lower()

            # Try to match against known patterns
            for pattern, cat_type in self.CATEGORY_PATTERNS.items():
                if pattern in quiz_name:
                    return cat_type

        return ""

    def get_difficulty_from_url(self, url: str) -> int:
        """Estimate difficulty from URL patterns.

        Returns 1-5 scale.
        """
        url_lower = url.lower()

        if any(w in url_lower for w in ["easy", "simple", "basic", "intro"]):
            return 1
        elif any(w in url_lower for w in ["medium", "intermediate"]):
            return 3
        elif any(w in url_lower for w in ["hard", "difficult", "advanced", "challenge"]):
            return 5
        elif any(w in url_lower for w in ["01", "02", "03"]):
            return 2  # Early numbered quizzes tend to be easier
        elif any(w in url_lower for w in ["08", "09", "10"]):
            return 4  # Later numbered quizzes tend to be harder

        return 3  # Default to medium
