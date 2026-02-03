# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DeepTutor is an AI-powered 11+ exam preparation platform targeting UK GL Assessment format for Year 5 students. It covers English, Maths, Verbal Reasoning (21 question types), and Non-Verbal Reasoning. The question bank contains ~5,949 questions.

## Development Commands

### Backend (FastAPI + Python)

```bash
# From project root - one-time setup
cd backend && uv venv && uv pip install -e .

# Seed database with questions (runs automatically on startup unless SKIP_SEEDING=true)
cd backend && uv run python scripts/seed_questions.py

# Run backend dev server (port 8000)
cd backend && uv run uvicorn app.main:app --reload

# Lint
cd backend && uv run ruff check app/

# Run tests
cd backend && uv run pytest
cd backend && uv run pytest tests/test_specific.py -v  # single test file
```

### Frontend (Next.js 15 + React 19 + TypeScript)

```bash
# Install dependencies
cd frontend && npm install

# Run frontend dev server (port 3000)
cd frontend && npm run dev

# Build (static export to out/)
cd frontend && npm run build

# Lint
cd frontend && npm run lint
```

### Full Setup

```bash
./run.sh  # Sets up both backend and frontend, seeds database
```

### Deployment

```bash
# Backend to Google Cloud Run
GOOGLE_CLOUD_PROJECT=booming-order-424821-m1 scripts/deploy_backend.sh

# Frontend to Cloudflare Pages (build with production API URL, then deploy static output)
cd frontend && NEXT_PUBLIC_API_URL=https://deeptutor-backend-400481200537.us-central1.run.app npm run build
cd frontend && wrangler pages deploy out --project-name=deeptutor --commit-dirty=true
```

Production URLs:
- Frontend: https://deeptutor.pages.dev
- Backend: https://deeptutor-backend-400481200537.us-central1.run.app

## Architecture

### Two-service architecture

- **Backend**: FastAPI (Python 3.10+) at `backend/` - REST API with SQLite (dev) / PostgreSQL (prod)
- **Frontend**: Next.js 15 at `frontend/` - static export (no SSR), deployed as static site

The frontend is configured with `output: "export"` in `next.config.js`, producing a fully static site served by Nginx on Cloud Run or Cloudflare Pages.

### Backend structure

```
backend/app/
  main.py           - FastAPI app entry point, CORS config, router mounting
  config.py         - Settings: DB URL, API keys, session defaults
  routers/          - API endpoints (questions, practice, progress, users, visualize, research, generator)
  services/         - Business logic (question_bank, practice, progress_tracker, llm_generator)
  models/           - Pydantic models (question, user, progress)
  db/database.py    - Async SQLAlchemy session setup
  db/models.py      - ORM models (users, questions, practice_sessions, user_answers, progress)
  api/auth.py       - JWT authentication
  crawlers/         - Web scraping for GL Assessment materials
```

### Frontend structure

```
frontend/
  app/              - Next.js App Router pages (dashboard, practice/[sessionId], progress, mock-exam, smart-practice, visualize, research)
  components/       - React components (Sidebar, questions/MultipleChoice|FillInBlank|VisualPattern, ui/)
  lib/api.ts        - API client - uses NEXT_PUBLIC_API_URL env var, falls back to production Cloud Run URL
  context/          - React context providers
```

### Data flow

1. Questions are stored as JSON files in `backend/data/questions/` and seeded into SQLite at startup
2. `deployment_dump.json` is the master seed file for Cloud Run deployments
3. Question content, answers, and hints are stored as JSON columns in the database
4. Frontend communicates via REST API - all state is server-side

### Key API routes

All routes are prefixed with `/api/`:
- `questions/` - CRUD, answer checking, hints
- `practice/` - Session lifecycle (start, next question, answer, complete)
- `progress/{userId}` - Analytics, weakness detection, recommendations
- `users/` - User management
- `auth/` - JWT login/register
- `visualize/` - Mermaid diagram generation via LLM
- `research/` - Web-augmented Q&A

### AI integrations

The backend integrates with Gemini (primary), OpenAI, and Anthropic APIs for:
- Answer explanations and hints
- Question generation (`services/llm_generator.py`)
- Visual concept diagrams (`routers/visualize.py`)
- Web-augmented research (`routers/research.py`)

API keys are configured via `.env` in backend root. Users can also set their preferred AI provider via frontend settings (stored in localStorage).

## Configuration

### Backend `.env`

```
GEMINI_API_KEY=...
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
```

### Frontend `.env.local`

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

If `NEXT_PUBLIC_API_URL` is not set, the frontend falls back to the production Cloud Run URL hardcoded in `lib/api.ts`.

### Cloud Run deployment

Backend uses `SKIP_SEEDING=true` and `DATABASE_URL=sqlite+aiosqlite:////tmp/tutor.db` in production. The `/tmp` database is ephemeral - persistent data requires a volume mount (configured in `fly.toml` for Fly.io).

## Code Style

### Python (ruff)
- Line length: 100
- Rules: E, F, I, N, W
- Target: Python 3.10

### Frontend
- TypeScript with ESLint (Next.js config)
- TailwindCSS for styling
- Radix UI for unstyled accessible components
- Lucide React for icons

## Important Patterns

- Question data uses flexible JSON schemas - `content`, `answer`, and `hints` fields are JSON columns that vary by question type
- Practice sessions track per-question timing and hint usage, with score penalties (0.5 per hint) defined in `config.py`
- The database auto-seeds from JSON files on startup unless `SKIP_SEEDING=true` is set
- CORS is configured in `main.py` with specific allowed origins for dev/staging/production
- Frontend uses dynamic route `practice/[sessionId]` for active practice sessions
- Images for NVR questions are served from `backend/data/images/` via a static mount at `/images/*`
