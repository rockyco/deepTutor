# 11+ Deep Tutor

AI-powered interactive learning platform for UK 11+ exam preparation, specifically targeting GL Assessment format for Year 5 students.

## Features

- **Four Subject Areas**: English, Maths, Verbal Reasoning, Non-verbal Reasoning
- **21 Verbal Reasoning Question Types**: Covering all GL Assessment question formats
- **Interactive Practice**: Immediate feedback with detailed explanations
- **Adaptive Difficulty**: Questions adjust based on performance
- **Progress Tracking**: Monitor improvement over time
- **Timed Practice**: Simulate exam conditions
- **Hints System**: Progressive hints to guide learning

## Project Structure

```
deepTutor/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── models/         # Pydantic models
│   │   ├── routers/        # API endpoints
│   │   ├── services/       # Business logic
│   │   └── db/             # Database layer
│   ├── data/
│   │   ├── questions/      # Question bank (JSON)
│   │   └── materials/      # Downloaded GL materials
│   └── scripts/            # Utility scripts
├── frontend/               # Next.js frontend
│   ├── app/               # App router pages
│   ├── components/        # React components
│   └── lib/               # Utilities and API client
└── SPEC.md                # Project specification
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- uv (Python package manager)

### Backend Setup

```bash
cd backend

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# Seed the database with sample questions
uv run python scripts/seed_questions.py

# (Optional) Download GL Assessment materials
uv run python scripts/download_materials.py

# Run the backend server
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Visit http://localhost:3000 to use the application.

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## GL Assessment 11+ Exam Format

| Subject | Duration | Questions | Format |
|---------|----------|-----------|--------|
| English | 50 min | 49-56 | Comprehension, grammar, spelling |
| Maths | 50 min | 50 | KS2 curriculum, multiple choice |
| Verbal Reasoning | 50-60 min | 80 | 21 question types |
| Non-verbal Reasoning | 40 min | ~40 | Visual/spatial patterns |

## Question Types

### Verbal Reasoning (21 Types)
1. Insert a Letter
2. Two Odd Ones Out
3. Alphabet Code
4. Synonyms
5. Hidden Word
6. Missing Word (Cloze)
7. Number Series
8. Letter Series
9. Number Connections
10. Word Pairs/Analogies
11. Multiple Meaning
12. Letter Relationships
13. Number Codes
14. Compound Words
15. Word Shuffling
16. Anagrams
17. Logic Problems
18. Explore the Facts
19. Solve the Riddle
20. Rhyming Synonyms
21. Shuffled Sentences

### Non-verbal Reasoning
- Sequences
- Odd One Out
- Analogies
- Matrices
- Rotation
- Reflection
- 3D/Spatial
- Codes

## Question Database

| Subject | Questions |
|---------|-----------|
| Maths | 3,056 |
| English | 1,472 |
| Verbal Reasoning | 1,393 |
| Non-Verbal Reasoning | 28 |
| **Total** | **5,949** |

## Deployment (Cloudflare)

### Prerequisites

1. Install Wrangler CLI: `npm install -g wrangler`
2. Login to Cloudflare: `wrangler login`

### Deploy Backend (Cloudflare Workers)

```bash
cd backend

# Create D1 database
wrangler d1 create deep-tutor-db
# Update wrangler.toml with the database_id

# Deploy
wrangler deploy
```

### Deploy Frontend (Cloudflare Pages)

1. Push to GitHub
2. Connect repository to Cloudflare Pages
3. Set build command: `npm run build`
4. Set output directory: `.next`
5. Add environment variable: `NEXT_PUBLIC_API_URL=https://deep-tutor-api.workers.dev`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

AGPL-3.0

## Acknowledgments

- Inspired by [DeepTutor](https://github.com/HKUDS/DeepTutor)
- GL Assessment for providing free familiarisation materials
