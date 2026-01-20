#!/usr/bin/env python3
"""Comprehensive question data cleanup script.

Fixes:
1. Removes badly parsed PDF questions (examberry)
2. Cleans educationquizzes questions (removes numbering, validates answers)
3. Validates question-answer consistency
4. Removes questions with meaningless content
"""

import json
import re
import sqlite3
from pathlib import Path


def get_db_connection():
    """Get database connection."""
    db_path = Path(__file__).parent.parent / "data" / "tutor.db"
    return sqlite3.connect(db_path)


def is_garbage_text(text: str) -> bool:
    """Check if text is garbage/parsing artifact."""
    if not text:
        return True

    garbage_patterns = [
        r'^nswer',  # Broken "Answer" text
        r'^\[[\d\s]*mark',  # "[1 mark]" etc
        r'^[A-Z]\s*$',  # Single letter
        r'^\.\.\.',  # Ellipsis only
        r'^…+',  # Unicode ellipsis
        r'ND OF EXAMINATION',
        r'Fill in the table',
        r'Write a formula',
        r'^\s*$',  # Empty/whitespace
    ]

    for pattern in garbage_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True

    # Too short to be meaningful
    if len(text.strip()) < 5:
        return True

    return False


def is_valid_option(option: str) -> bool:
    """Check if an option is valid (not garbage)."""
    if not option:
        return False

    invalid_patterns = [
        r'^nswer',
        r'^\[[\d\s]*mark',
        r'^Fill in',
        r'^Write a',
        r'^ND OF',
        r'^Section',
        r'^\(\d+\)',  # (1), (2), etc alone
        r'^[a-d]\)',  # a), b) alone
        r'ach letter should',  # Instructions
        r'onsecutive letters',  # Instructions
        r'^\d+\s*,\s*\d+',  # Number lists like "1, 2, 3, 5"
        r'^[A-Z][a-z]+\s+\d{2}:\d{2}',  # Timetable entries "Croyden 22:56"
        r'haracter What we learn',  # Table headers
        r'^The\s+\w+comer$',  # "The latecomer" type instructions
        r'^The\s+couple$',
        r'^The\s+Red\s+Rock',
        r'^radley\s+Garrett',  # Broken names
        r'ast\s+Croyden',  # Broken location names
        r'lapham\s+Junc',
        r'train\s+leaves',  # Instructions
        r'\d+\s*mins?\s+[A-Z]\s+\d+',  # "6 mins B 10 mins" patterns
        r'\(\s*\?\s*\)',  # Question placeholders like "(?) "
        r'^Complete\s+the\s+table',  # Instructions
        r'^How\s+many\s+\w+\s+(would|squares)',  # Instructions
        r'hild\'s\s+frightened',  # Broken text
        r'hange\.$',  # Single broken word
        r'^\d+\.?\d*,\s*\d+\.?\d*,\s*X,',  # Sequence patterns with X
        r'^[A-Z][a-z]+\'s\s+(Eve|Day)\s+[A-Z]',  # "New Year's Eve B Boxing Day"
        r'^Tanya\s+mixes',  # Specific broken text
        r'^A\s+drink\s+is\s+made',  # Specific broken text
        r'\(adjective\)$',  # Word definitions as options
        r'\(noun\)$',
        r'\(verb\)$',
        r'^\w+\s+\(\?\)\s+\w+',  # Pattern like "edi (?) idy"
        r'^nd\s+£',  # Broken fragments
        r'^heaper\s+and',  # Broken fragments
        r'^ssay$',  # Broken text
        r'^NGLISH$',  # Broken text
        r'^ear\s+X\s+ant',  # Broken patterns
        r'^in\s+Y\s+bin',  # Broken patterns
        r'^us\s+Z\s+age',  # Broken patterns
        r'^\([\w\s]+\)\s+\([\w\s]+\)',  # Pattern like "(fair hair air) (self daft craft)"
    ]

    for pattern in invalid_patterns:
        if re.search(pattern, option, re.IGNORECASE):
            return False

    return len(option.strip()) >= 1


def is_question_format_broken(content: dict, answer: dict) -> bool:
    """Check if the question format is fundamentally broken."""
    text = content.get('text', '') or ''
    options = content.get('options') or []
    answer_value = answer.get('value', '') if answer else ''

    # Answer is same as one of the number list options (e.g., "1, 2, 3, 5")
    if answer_value and re.match(r'^\d+\s*,\s*\d+', answer_value):
        return True

    # Answer contains table header patterns
    if answer_value and re.search(r'haracter\s+What\s+we\s+learn', answer_value):
        return True

    # Answer contains question placeholders like "(?) "
    if answer_value and re.search(r'\(\s*\?\s*\)', answer_value):
        return True

    # Answer contains instructions
    instruction_patterns = [
        r'^Complete\s+the',
        r'^How\s+many',
        r'hild\'s\s+frightened',
        r'^Tanya\s+mixes',
        r'^A\s+drink\s+is\s+made',
        r'\(adjective\)$',
        r'\(noun\)$',
        r'\(verb\)$',
        r'^[A-Z][a-z]+\'s\s+(Eve|Day)\s+[A-Z]',  # "New Year's Eve B Boxing Day"
        r'^FOUR\s+HALF\s+ROPE',  # Word lists
        r'^\([\w\s]+\)\s+\([\w\s]+\)',  # Pattern like "(fair hair air) (self daft craft)"
        r'^His\s+[A-Z]+\s+had',  # Sentence patterns
        r'^ear\s+X\s+ant',  # Broken patterns
        r'^-?\d+\s*[-+]\s*\d+\s*[-+]',  # Equations like "-8 - 10 - 4 + 10"
        r'^nd\s+£',  # Broken fragments
        r'^NGLISH$',  # Broken text
        r'^ssay$',  # Broken text
        r'heaper\s+and\s+by',  # Broken text
    ]
    for pattern in instruction_patterns:
        if re.search(pattern, answer_value, re.IGNORECASE):
            return True

    # Answer is all caps multiple words (likely word lists/codes, not actual answers)
    if answer_value and re.match(r'^[A-Z]+(\s+[A-Z]+){2,}$', answer_value):
        return True

    # Question asks to "write down" or "support with quotation" - open-ended
    if re.search(r'Write\s+down|Support.*quotation|Write.*below', text, re.IGNORECASE):
        return True

    # Options are timetable entries
    if any(re.search(r'\d{2}:\d{2}\s+\d{2}:\d{2}', opt) for opt in options):
        return True

    # Answer is a scrambled/jumbled word (for anagram questions where answer is scrambled)
    if 'jumbled' in text.lower() and answer_value:
        # Check if answer is in all caps (likely the scrambled word, not solution)
        if answer_value.isupper() and len(answer_value) > 3:
            # Check if it's not a valid English word (basic check)
            if not any(answer_value == opt for opt in options if not opt.isupper()):
                return True

    return False


def clean_question_text(text: str) -> str:
    """Clean question text by removing numbering and artifacts."""
    if not text:
        return text

    # Remove leading question numbers like "10 ." or "3."
    text = re.sub(r'^\d+\s*\.\s*', '', text)

    # Remove trailing whitespace
    text = text.strip()

    return text


def fix_vr_word_relationship_question(content: dict, answer: dict) -> tuple:
    """
    Fix verbal reasoning questions where options contain example lines.

    Pattern: Options like ['a. grid (dire) heed', 'b. juts (?) debt', 'stun', 'stub']
    Should be: Examples in text, options = ['stun', 'stub'], answer = correct choice
    """
    options = content.get('options', [])
    if len(options) != 4:
        return None, None

    # Check if first two options are example lines
    if not (options[0].startswith('a.') and options[1].startswith('b.')):
        return None, None

    # Extract the actual answer options (last 2)
    real_options = options[2:]

    # The answer should be one of the real options, not the example
    # For these questions, we can't determine the correct answer without solving
    # So we'll mark them as needing manual review or delete them
    return None, None  # Mark for deletion - can't auto-fix


def validate_answer_in_options(answer: dict, options: list) -> bool:
    """Check if answer value is in the options list."""
    if not options or not answer:
        return True  # Can't validate without options

    answer_value = answer.get('value', '')
    if not answer_value:
        return False

    # Check exact match
    if answer_value in options:
        return True

    # Check case-insensitive match
    answer_lower = answer_value.lower().strip()
    for opt in options:
        if opt.lower().strip() == answer_lower:
            return True

    return False


def analyze_questions(conn) -> dict:
    """Analyze all questions and categorize by quality."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, subject, question_type, content, answer, source FROM questions")

    stats = {
        'total': 0,
        'valid': 0,
        'pdf_garbage': 0,
        'invalid_options': 0,
        'answer_mismatch': 0,
        'garbage_text': 0,
        'to_delete': [],
        'to_update': [],
    }

    for row in cursor.fetchall():
        qid, subject, qtype, content_json, answer_json, source = row
        stats['total'] += 1

        try:
            content = json.loads(content_json) if content_json else {}
            answer = json.loads(answer_json) if answer_json else {}
        except json.JSONDecodeError:
            stats['to_delete'].append((qid, 'invalid_json'))
            continue

        text = content.get('text', '') or content.get('passage', '')
        options = content.get('options', [])

        # Check for examberry PDF garbage
        if source and 'examberrypapers.co.uk' in source:
            # Most PDF extractions are garbage
            if options:
                valid_opts = [o for o in options if is_valid_option(o)]
                if len(valid_opts) < 2:
                    stats['pdf_garbage'] += 1
                    stats['to_delete'].append((qid, 'pdf_garbage'))
                    continue

            if is_garbage_text(text):
                stats['pdf_garbage'] += 1
                stats['to_delete'].append((qid, 'pdf_garbage_text'))
                continue

        # Check for garbage text in any source
        if is_garbage_text(text):
            stats['garbage_text'] += 1
            stats['to_delete'].append((qid, 'garbage_text'))
            continue

        # Check options validity
        if options:
            valid_opts = [o for o in options if is_valid_option(o)]
            if len(valid_opts) < 2:
                stats['invalid_options'] += 1
                stats['to_delete'].append((qid, 'invalid_options'))
                continue

        # Check answer-options consistency for multiple choice
        if options and answer:
            if not validate_answer_in_options(answer, options):
                stats['answer_mismatch'] += 1
                stats['to_delete'].append((qid, 'answer_mismatch'))
                continue

        # Check for broken question formats
        if is_question_format_broken(content, answer):
            stats.setdefault('format_broken', 0)
            stats['format_broken'] += 1
            stats['to_delete'].append((qid, 'format_broken'))
            continue

        # Check if text needs cleaning
        cleaned_text = clean_question_text(text)
        if cleaned_text != text:
            stats['to_update'].append((qid, content, cleaned_text))

        stats['valid'] += 1

    return stats


def cleanup_database(conn, stats: dict, dry_run: bool = True):
    """Clean up the database based on analysis."""
    cursor = conn.cursor()

    if dry_run:
        print("\n=== DRY RUN MODE ===")
        print("No changes will be made. Run with --apply to apply changes.\n")

    # Delete invalid questions
    if stats['to_delete']:
        print(f"\n{'Would delete' if dry_run else 'Deleting'} {len(stats['to_delete'])} invalid questions:")

        by_reason = {}
        for qid, reason in stats['to_delete']:
            by_reason.setdefault(reason, []).append(qid)

        for reason, ids in by_reason.items():
            print(f"  - {reason}: {len(ids)} questions")

        if not dry_run:
            for qid, reason in stats['to_delete']:
                cursor.execute("DELETE FROM questions WHERE id = ?", (qid,))
            conn.commit()
            print(f"Deleted {len(stats['to_delete'])} questions.")

    # Update questions with cleaned text
    if stats['to_update']:
        print(f"\n{'Would update' if dry_run else 'Updating'} {len(stats['to_update'])} questions with cleaned text")

        if not dry_run:
            for qid, content, cleaned_text in stats['to_update']:
                content['text'] = cleaned_text
                cursor.execute(
                    "UPDATE questions SET content = ? WHERE id = ?",
                    (json.dumps(content), qid)
                )
            conn.commit()
            print(f"Updated {len(stats['to_update'])} questions.")


def print_stats(stats: dict):
    """Print analysis statistics."""
    print("\n" + "=" * 50)
    print("QUESTION DATABASE ANALYSIS")
    print("=" * 50)
    print(f"Total questions:       {stats['total']:,}")
    print(f"Valid questions:       {stats['valid']:,}")
    print(f"PDF garbage:           {stats['pdf_garbage']:,}")
    print(f"Invalid options:       {stats['invalid_options']:,}")
    print(f"Answer mismatch:       {stats['answer_mismatch']:,}")
    print(f"Garbage text:          {stats['garbage_text']:,}")
    print(f"To be deleted:         {len(stats['to_delete']):,}")
    print(f"To be updated:         {len(stats['to_update']):,}")
    print("=" * 50)


def main():
    import sys

    dry_run = '--apply' not in sys.argv

    print("Question Database Cleanup Tool")
    print("-" * 30)

    conn = get_db_connection()

    print("Analyzing questions...")
    stats = analyze_questions(conn)
    print_stats(stats)

    cleanup_database(conn, stats, dry_run=dry_run)

    if dry_run:
        print("\nRun with --apply to apply the changes.")
    else:
        # Final count
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM questions")
        final_count = cursor.fetchone()[0]
        print(f"\nFinal question count: {final_count:,}")

    conn.close()


if __name__ == "__main__":
    main()
