"""Analyze and clean incomplete questions from the database."""

import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "tutor.db"

def analyze_questions():
    """Analyze questions for integrity issues."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=" * 60)
    print("QUESTION DATABASE ANALYSIS")
    print("=" * 60)
    
    # Total count
    cursor.execute("SELECT COUNT(*) as total FROM questions")
    total = cursor.fetchone()["total"]
    print(f"\nTotal questions: {total}")
    
    # By subject
    print("\n--- By Subject ---")
    cursor.execute("SELECT subject, COUNT(*) as count FROM questions GROUP BY subject ORDER BY count DESC")
    for row in cursor.fetchall():
        print(f"  {row['subject']}: {row['count']}")
    
    # By question type
    print("\n--- By Question Type ---")
    cursor.execute("SELECT question_type, COUNT(*) as count FROM questions GROUP BY question_type ORDER BY count DESC LIMIT 15")
    for row in cursor.fetchall():
        print(f"  {row['question_type']}: {row['count']}")
    
    # Find problematic questions
    print("\n--- PROBLEMATIC QUESTIONS ---")
    
    issues = []
    cursor.execute("SELECT id, subject, question_type, content, answer FROM questions")
    for row in cursor.fetchall():
        qid = row["id"]
        subject = row["subject"]
        qtype = row["question_type"]
        content_str = row["content"]
        answer_str = row["answer"]
        
        problems = []
        
        # Check content
        if not content_str or content_str == "{}":
            problems.append("Empty content")
        else:
            try:
                content = json.loads(content_str)
                if not content.get("text"):
                    problems.append("Missing question text")
                # Check for multiple_choice without options
                if row["question_type"] == "multiple_choice" and not content.get("options"):
                    problems.append("Multiple choice without options")
            except json.JSONDecodeError:
                problems.append("Invalid content JSON")
        
        # Check answer
        if not answer_str or answer_str == "{}":
            problems.append("Empty answer")
        else:
            try:
                answer = json.loads(answer_str)
                if not answer.get("value"):
                    problems.append("Missing answer value")
            except json.JSONDecodeError:
                problems.append("Invalid answer JSON")
        
        if problems:
            issues.append({
                "id": qid,
                "subject": subject,
                "type": qtype,
                "problems": problems
            })
    
    if issues:
        print(f"\nFound {len(issues)} problematic questions:")
        for issue in issues[:20]:  # Show first 20
            print(f"  [{issue['subject']}/{issue['type']}] {issue['id'][:8]}... : {', '.join(issue['problems'])}")
        if len(issues) > 20:
            print(f"  ... and {len(issues) - 20} more")
    else:
        print("\nNo problematic questions found!")
    
    conn.close()
    return issues

def delete_problematic_questions(dry_run=True):
    """Delete questions with integrity issues."""
    issues = analyze_questions()
    
    if not issues:
        print("\nNo questions to delete.")
        return
    
    if dry_run:
        print(f"\n[DRY RUN] Would delete {len(issues)} questions.")
        print("Run with dry_run=False to actually delete.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    ids_to_delete = [issue["id"] for issue in issues]
    placeholders = ",".join("?" * len(ids_to_delete))
    
    cursor.execute(f"DELETE FROM questions WHERE id IN ({placeholders})", ids_to_delete)
    conn.commit()
    
    print(f"\nDeleted {cursor.rowcount} problematic questions.")
    conn.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--delete":
        delete_problematic_questions(dry_run=False)
    else:
        analyze_questions()
        print("\nTo delete problematic questions, run with: python analyze_questions.py --delete")
