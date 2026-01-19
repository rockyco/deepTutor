# 11+ Deep Tutor - Project Specification

## Overview

An AI-powered interactive learning platform to help Year 5 students master the UK 11+ exam, specifically targeting GL Assessment format. The platform provides personalized practice, explanations, and progress tracking across all four exam subjects.

## Target Exam: GL Assessment 11+

GL Assessment provides 11+ exams for over 80% of grammar schools in England. The exam covers:

| Subject | Duration | Questions | Format |
|---------|----------|-----------|--------|
| English | 50 min | 49-56 | Comprehension, grammar, spelling |
| Maths | 50 min | 50 | KS2 curriculum, multiple choice |
| Verbal Reasoning | 50-60 min | 80 | 21 question types |
| Non-verbal Reasoning | 40 min | ~40 | Visual/spatial patterns |

## Core Features

### 1. Question Bank System
- Structured database of questions by subject, type, and difficulty
- Support for multiple question formats (multiple choice, fill-in, drag-drop)
- Ability to crawl and parse external question resources
- Question generation using AI for practice variety

### 2. Subject Modules

#### English Comprehension
- Passage-based comprehension exercises
- Fiction, non-fiction, and poetry texts
- Sentence completion
- Grammar and spelling practice
- Vocabulary building

#### Mathematics
- Number operations (most common - ~5x other topics)
- Fractions, decimals, percentages
- Geometry and measurement
- Data handling
- Word problems
- Aligned with KS2 National Curriculum

#### Verbal Reasoning (21 Question Types)
| Type | Name | Description |
|------|------|-------------|
| A | Insert a Letter | Complete word before/after brackets |
| B | Two Odd Ones Out | Find two words different from others |
| C | Alphabet Code | Decode words using letter shifts |
| D | Synonyms | Find closest meaning words |
| E | Hidden Word | Find word hidden across words |
| F | Missing Word (Cloze) | Complete word with missing letters |
| G | Number Series | Complete number patterns |
| H | Letter Series | Complete letter patterns |
| I | Number Connections | Find relationships between numbers |
| J | Word Pairs/Analogies | Complete word relationships |
| K | Multiple Meaning | Find word fitting multiple contexts |
| L | Letter Relationships | Complete letter pair patterns |
| M | Number Codes | Decode words using number codes |
| N | Compound Words | Form compound words |
| O | Word Shuffling | Rearrange words into sentences |
| P | Anagrams | Rearrange letters to form words |
| Q | Logic Problems | Solve logical deduction puzzles |
| R | Explore the Facts | Answer questions from given facts |
| S | Solve the Riddle | Solve word riddles |
| T | Rhyming Synonyms | Find rhyming word pairs |
| U | Shuffled Sentences | Reorder shuffled sentences |

#### Non-verbal Reasoning
- **Sequences**: Identify pattern continuation
- **Odd One Out**: Find the shape that doesn't belong
- **Analogies**: Shape relationship patterns
- **Matrices**: Complete 2D grid patterns
- **Rotation**: Identify rotated shapes
- **Reflection**: Mirror image identification
- **3D/Spatial**: Cube nets, folding, spatial visualization
- **Codes**: Shape-to-code relationships

### 3. Learning Features
- Step-by-step explanations for every answer
- Visual aids and interactive demonstrations
- Hints system (progressive revealing)
- Concept tutorials before practice
- Video-style walkthroughs for complex topics

### 4. Progress & Analytics
- Performance tracking by subject and question type
- Strengths and weaknesses identification
- Adaptive difficulty adjustment
- Timed practice mode (exam simulation)
- Progress reports for parents

### 5. Gamification
- Points and streaks for consistent practice
- Achievement badges
- Weekly challenges
- Leaderboards (optional)

## Technical Architecture

### Backend (FastAPI - Python 3.10+)
```
backend/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── models/              # Pydantic models
│   │   ├── question.py
│   │   ├── user.py
│   │   └── progress.py
│   ├── routers/             # API endpoints
│   │   ├── questions.py
│   │   ├── practice.py
│   │   ├── progress.py
│   │   └── explanations.py
│   ├── services/            # Business logic
│   │   ├── question_bank.py
│   │   ├── adaptive.py
│   │   ├── explanation_generator.py
│   │   └── progress_tracker.py
│   ├── crawlers/            # Content scrapers
│   │   └── gl_materials.py
│   └── db/                  # Database layer
│       ├── database.py
│       └── crud.py
├── data/
│   ├── questions/           # Question JSON files
│   └── materials/           # Downloaded GL materials
└── tests/
```

### Frontend (Next.js 14 + React + TailwindCSS)
```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx             # Landing/dashboard
│   ├── subjects/
│   │   ├── english/
│   │   ├── maths/
│   │   ├── verbal-reasoning/
│   │   └── non-verbal-reasoning/
│   ├── practice/
│   │   └── [sessionId]/
│   └── progress/
├── components/
│   ├── questions/           # Question type components
│   │   ├── MultipleChoice.tsx
│   │   ├── FillInBlank.tsx
│   │   ├── DragDrop.tsx
│   │   └── VisualPattern.tsx
│   ├── explanations/
│   ├── progress/
│   └── ui/
├── lib/
│   ├── api.ts
│   └── hooks/
└── public/
    └── images/
```

### Database Schema (SQLite/PostgreSQL)
```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY,
    name TEXT,
    year_group INTEGER DEFAULT 5,
    created_at TIMESTAMP
);

-- Questions
CREATE TABLE questions (
    id UUID PRIMARY KEY,
    subject TEXT NOT NULL,  -- english, maths, verbal, nonverbal
    question_type TEXT NOT NULL,
    difficulty INTEGER,     -- 1-5
    content JSONB,          -- Question data
    answer JSONB,           -- Correct answer(s)
    explanation TEXT,
    hints JSONB,            -- Progressive hints
    source TEXT,            -- Origin of question
    created_at TIMESTAMP
);

-- Practice Sessions
CREATE TABLE practice_sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    subject TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    score INTEGER,
    total_questions INTEGER
);

-- Answers
CREATE TABLE user_answers (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES practice_sessions(id),
    question_id UUID REFERENCES questions(id),
    user_answer JSONB,
    is_correct BOOLEAN,
    time_taken INTEGER,     -- seconds
    hints_used INTEGER,
    created_at TIMESTAMP
);

-- Progress
CREATE TABLE progress (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    subject TEXT,
    question_type TEXT,
    total_attempted INTEGER,
    total_correct INTEGER,
    current_level INTEGER,
    last_practiced TIMESTAMP
);
```

## Data Sources

### Official GL Assessment Materials
- Verbal Reasoning familiarisation: https://cdn.shopify.com/s/files/1/0681/5498/2630/files/verbal-reasoning.zip
- Non-verbal Reasoning: https://cdn.shopify.com/s/files/1/0681/5498/2630/files/non-verbal-reasoning.zip
- English: https://cdn.shopify.com/s/files/1/0681/5498/2630/files/english_1.zip
- Maths: https://cdn.shopify.com/s/files/1/0681/5498/2630/files/maths.zip

### Additional Resources
- Free practice papers from educational sites
- KS2 curriculum aligned content
- AI-generated practice questions (with human review)

## User Flow

1. **Onboarding**: Select target schools, set practice goals
2. **Assessment**: Initial diagnostic test to identify starting level
3. **Dashboard**: Overview of progress, recommended practice
4. **Practice Session**:
   - Choose subject or take mixed practice
   - Answer questions with immediate feedback
   - View detailed explanations
   - Track time per question
5. **Review**: Analyze mistakes, revisit weak areas
6. **Mock Exams**: Full timed practice tests

## API Endpoints

### Questions
- `GET /api/questions?subject=&type=&difficulty=` - Get questions
- `POST /api/questions/check` - Check answer, get explanation
- `GET /api/questions/{id}/hints` - Get progressive hints

### Practice
- `POST /api/practice/start` - Start practice session
- `POST /api/practice/{id}/answer` - Submit answer
- `GET /api/practice/{id}/results` - Get session results

### Progress
- `GET /api/progress` - Get user progress overview
- `GET /api/progress/weaknesses` - Get areas needing practice
- `GET /api/progress/recommendations` - Get recommended practice

## MVP Scope (Phase 1)

1. Basic question bank with 100+ questions per subject
2. Multiple choice and fill-in question types
3. Immediate feedback with explanations
4. Simple progress tracking
5. Timed practice mode

## Future Enhancements (Phase 2+)

- AI tutoring chat for concept explanation
- Parent dashboard with progress reports
- Multiplayer challenges
- Mobile app (React Native)
- Voice-based practice mode
- Integration with school curricula

## Success Metrics

- Time spent practicing per week
- Question accuracy improvement over time
- Subject weakness identification accuracy
- User retention and engagement
- Mock exam score correlation with real exam results
