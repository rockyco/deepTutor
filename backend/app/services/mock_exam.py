"""Mock exam service for GL Assessment format exams."""

import json
import logging
import random
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MockExamSessionDB, QuestionDB
from app.models.mock_exam import (
    PAPER_SECTIONS,
    PAPERS_PER_EXAM,
    ExamSection,
    MockExamAnswer,
    MockExamResult,
    MockExamSession,
    PaperResult,
    PaperStructure,
    SectionQuestions,
    SectionResult,
)

logger = logging.getLogger(__name__)

# Subject to question_type mapping for selection
SECTION_QUERY_MAP = {
    ExamSection.ENGLISH: {
        "subject": "english",
        "subtypes": {
            "comprehension": ["comprehension"],
            "vocabulary": [
                "vocabulary", "grammar", "spelling", "sentence_completion", "punctuation",
            ],
        },
    },
    ExamSection.MATHS: {
        "subject": "maths",
        "types": [
            "number_operations", "fractions", "decimals", "percentages",
            "geometry", "measurement", "data_handling", "word_problems",
            "algebra", "ratio",
        ],
    },
    ExamSection.NON_VERBAL_REASONING: {
        "subject": "non_verbal_reasoning",
        "types": [
            "nvr_sequences", "nvr_odd_one_out", "nvr_analogies",
            "nvr_matrices", "nvr_rotation", "nvr_reflection",
            "nvr_spatial_3d", "nvr_codes", "nvr_visual",
        ],
    },
    ExamSection.VERBAL_REASONING: {
        "subject": "verbal_reasoning",
        "types": [
            "vr_insert_letter", "vr_odd_ones_out", "vr_alphabet_code",
            "vr_synonyms", "vr_hidden_word", "vr_missing_word",
            "vr_number_series", "vr_letter_series", "vr_number_connections",
            "vr_word_pairs", "vr_multiple_meaning", "vr_letter_relationships",
            "vr_number_codes", "vr_compound_words", "vr_word_shuffling",
            "vr_anagrams", "vr_logic_problems", "vr_explore_facts",
            "vr_solve_riddle", "vr_rhyming_synonyms", "vr_shuffled_sentences",
        ],
    },
}


class MockExamService:
    """Service for managing mock exams."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_questions_for_section(
        self,
        section: ExamSection,
        count: int,
        exclude_ids: set[str],
        subtypes: dict[str, int] | None = None,
    ) -> list[str]:
        """Fetch question IDs for a section, respecting exclusions."""
        config = SECTION_QUERY_MAP[section]
        subject = config["subject"]

        if subtypes:
            # English: fetch by subtype counts
            all_ids = []
            for subtype_name, subtype_count in subtypes.items():
                type_list = config.get("subtypes", {}).get(subtype_name, [subtype_name])
                query = (
                    select(QuestionDB.id)
                    .where(QuestionDB.subject == subject)
                    .where(QuestionDB.question_type.in_(type_list))
                )
                if exclude_ids:
                    query = query.where(~QuestionDB.id.in_(exclude_ids))

                result = await self.db.execute(query)
                available = [r[0] for r in result.all()]
                random.shuffle(available)
                selected = available[:subtype_count]
                all_ids.extend(selected)
                exclude_ids.update(selected)
            return all_ids
        else:
            # Other subjects: fetch by subject, any matching type
            types = config.get("types", [])
            query = select(QuestionDB.id).where(QuestionDB.subject == subject)
            if types:
                query = query.where(QuestionDB.question_type.in_(types))
            if exclude_ids:
                query = query.where(~QuestionDB.id.in_(exclude_ids))

            result = await self.db.execute(query)
            available = [r[0] for r in result.all()]
            random.shuffle(available)
            selected = available[:count]
            exclude_ids.update(selected)
            return selected

    async def create_exam(self, user_id: str, exam_number: int = 1) -> MockExamSession:
        """Create a new mock exam with 2 papers."""
        used_ids: set[str] = set()
        papers = []

        for paper_num in range(1, PAPERS_PER_EXAM + 1):
            sections = []
            for i, section_config in enumerate(PAPER_SECTIONS):
                question_ids = await self._get_questions_for_section(
                    section=section_config.section,
                    count=section_config.question_count,
                    exclude_ids=used_ids,
                    subtypes=section_config.subtypes,
                )
                sections.append(SectionQuestions(
                    section=section_config.section,
                    section_index=i,
                    question_ids=question_ids,
                    question_count=len(question_ids),
                    time_seconds=section_config.time_seconds,
                ))

            papers.append(PaperStructure(
                paper_number=paper_num,
                sections=sections,
                total_questions=sum(s.question_count for s in sections),
            ))

        session = MockExamSession(
            user_id=user_id,
            exam_number=exam_number,
            papers=papers,
        )

        # Persist to DB
        db_session = MockExamSessionDB(
            id=session.id,
            user_id=user_id,
            exam_number=exam_number,
            data=json.dumps(session.model_dump(), default=str),
            status="in_progress",
        )
        self.db.add(db_session)
        await self.db.commit()

        return session

    async def get_exam(self, exam_id: str) -> MockExamSession | None:
        """Get an existing mock exam session."""
        result = await self.db.execute(
            select(MockExamSessionDB).where(MockExamSessionDB.id == exam_id)
        )
        db_session = result.scalar_one_or_none()
        if not db_session:
            return None
        data = json.loads(db_session.data)
        return MockExamSession(**data)

    async def submit_answer(
        self, exam_id: str, answer: MockExamAnswer
    ) -> dict:
        """Submit an answer for a question in the exam."""
        result = await self.db.execute(
            select(MockExamSessionDB).where(MockExamSessionDB.id == exam_id)
        )
        db_session = result.scalar_one_or_none()
        if not db_session:
            return {"error": "Exam not found"}

        data = json.loads(db_session.data)
        data["answers"][answer.question_id] = answer.user_answer
        data["answer_times"][answer.question_id] = answer.time_taken_seconds
        db_session.data = json.dumps(data, default=str)
        await self.db.commit()

        # Check answer
        q_result = await self.db.execute(
            select(QuestionDB).where(QuestionDB.id == answer.question_id)
        )
        question = q_result.scalar_one_or_none()
        if question:
            correct_answer = json.loads(question.answer)
            correct_value = correct_answer.get("value", "")
            is_correct = answer.user_answer.strip().lower() == correct_value.strip().lower()
            return {
                "is_correct": is_correct,
                "correct_answer": correct_value,
                "explanation": question.explanation,
            }
        return {"is_correct": False, "correct_answer": "", "explanation": ""}

    async def get_section_questions(
        self, exam_id: str, paper_num: int, section_index: int
    ) -> list[dict]:
        """Get full question data for a section."""
        session = await self.get_exam(exam_id)
        if not session:
            return []

        paper = next((p for p in session.papers if p.paper_number == paper_num), None)
        if not paper:
            return []

        if section_index >= len(paper.sections):
            return []

        section = paper.sections[section_index]
        questions = []
        for qid in section.question_ids:
            result = await self.db.execute(
                select(QuestionDB).where(QuestionDB.id == qid)
            )
            q = result.scalar_one_or_none()
            if q:
                questions.append({
                    "id": q.id,
                    "subject": q.subject,
                    "question_type": q.question_type,
                    "format": q.format,
                    "difficulty": q.difficulty,
                    "content": json.loads(q.content),
                    "explanation": q.explanation,
                })

        return questions

    async def complete_exam(self, exam_id: str) -> MockExamResult | None:
        """Complete an exam and calculate results."""
        result = await self.db.execute(
            select(MockExamSessionDB).where(MockExamSessionDB.id == exam_id)
        )
        db_session = result.scalar_one_or_none()
        if not db_session:
            return None

        data = json.loads(db_session.data)
        session = MockExamSession(**data)
        user_answers = session.answers
        answer_times = session.answer_times

        # Calculate results per paper and section
        paper_results = []
        total_correct = 0
        total_questions = 0
        total_time = 0
        subject_stats: dict[str, dict] = {}

        for paper in session.papers:
            section_results = []
            paper_correct = 0
            paper_total = 0
            paper_time = 0

            for section in paper.sections:
                section_correct = 0
                section_time = 0

                for qid in section.question_ids:
                    paper_total += 1
                    total_questions += 1

                    if qid in user_answers:
                        # Check answer
                        q_result = await self.db.execute(
                            select(QuestionDB).where(QuestionDB.id == qid)
                        )
                        q = q_result.scalar_one_or_none()
                        if q:
                            correct = json.loads(q.answer).get("value", "")
                            is_correct = (
                                user_answers[qid].strip().lower()
                                == correct.strip().lower()
                            )
                            if is_correct:
                                section_correct += 1
                                paper_correct += 1
                                total_correct += 1

                    section_time += answer_times.get(qid, 0)

                section_total = len(section.question_ids)
                section_results.append(SectionResult(
                    section=section.section,
                    total=section_total,
                    correct=section_correct,
                    accuracy=section_correct / section_total if section_total > 0 else 0,
                    time_used_seconds=section_time,
                ))

                # Aggregate by subject
                subj = section.section.value
                if subj not in subject_stats:
                    subject_stats[subj] = {"total": 0, "correct": 0, "time": 0}
                subject_stats[subj]["total"] += section_total
                subject_stats[subj]["correct"] += section_correct
                subject_stats[subj]["time"] += section_time

                paper_time += section_time

            paper_results.append(PaperResult(
                paper_number=paper.paper_number,
                sections=section_results,
                total_questions=paper_total,
                total_correct=paper_correct,
                accuracy=paper_correct / paper_total if paper_total > 0 else 0,
                total_time_seconds=paper_time,
            ))

            total_time += paper_time

        # Build subject breakdown
        subject_breakdown = {}
        for subj, stats in subject_stats.items():
            subject_breakdown[subj] = {
                "total": stats["total"],
                "correct": stats["correct"],
                "accuracy": stats["correct"] / stats["total"] if stats["total"] > 0 else 0,
                "time_seconds": stats["time"],
            }

        now = datetime.utcnow()

        # Update DB
        db_session.status = "completed"
        data["status"] = "completed"
        data["completed_at"] = now.isoformat()
        db_session.data = json.dumps(data, default=str)
        await self.db.commit()

        return MockExamResult(
            exam_id=exam_id,
            user_id=session.user_id,
            papers=paper_results,
            total_questions=total_questions,
            total_correct=total_correct,
            overall_accuracy=total_correct / total_questions if total_questions > 0 else 0,
            total_time_seconds=total_time,
            subject_breakdown=subject_breakdown,
            completed_at=now,
        )
