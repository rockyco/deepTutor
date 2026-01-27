---
name: CGP Question Extraction
description: Workflow to extract questions, images, and answers from CGP 11+ Online Tests and integrate them into DeepTutor.
---

# CGP Question Extraction Skill

This skill provides a set of scripts and instructions to extract content from CGP's automated 11+ practice tests.

## Workflow Overview

1. **Extract Images & Text**: Use Playwright to capture the main question image and option images, along with question text.
2. **Extract Answers**: Automate test submission to reveal correct answers.
3. **Merge Data**: Combine metadata and answers.
4. **Update Database**: Ingest the clean data into the local SQLite database.

## Directory Structure

```
skills/cgp_extraction/
├── SKILL.md            # This file
├── scripts/
│   ├── extract_images.py      # Captures visual content
│   ├── extract_answers.py     # Submits test to get answers
│   ├── merge_metadata.py      # Combines the two data sources
│   └── update_db.py           # Writes to database
```

## Step-by-Step Instructions

## Step-by-Step Instructions

### 1. Unified Extraction (Recommended)
Use `extract_unified.py` to run the complete workflow (Images -> Answers) in a single robust session.
```bash
# Syntax: python skills/cgp_extraction/scripts/extract_unified.py --subject [subject_key]
python skills/cgp_extraction/scripts/extract_unified.py --subject maths
python skills/cgp_extraction/scripts/extract_unified.py --subject non_verbal_reasoning
python skills/cgp_extraction/scripts/extract_unified.py --subject verbal_reasoning
python skills/cgp_extraction/scripts/extract_unified.py --subject english
```
This produces `metadata.json` directly in `backend/data/images/granular_[subject]`.

### 2. Update Database
Run `update_db.py` to scan all extracted data folders and ingest them into the SQLite database.
```bash
python skills/cgp_extraction/scripts/update_db.py
```

## Specific workflows

### Non-Verbal Reasoning (NVR) & Others
The unified script handles the specific complexities of each subject:
- **NVR**: Separates Question Figure from Option Images.
- **Maths/VR/English**: Robustly extracts answers even without explicit text labels, using DOM inspection.
- **Modal Handling**: Automatically handles the "Mark Test" confirmation popup.
