"""11+ Deep Tutor - FastAPI Application."""

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func

from app.config import settings
from app.db import init_db
from app.db.database import async_session
from app.db.models import QuestionDB
from app.routers import questions_router, practice_router, progress_router, users_router

logger = logging.getLogger(__name__)


async def seed_questions():
    """Seed database with questions from JSON files if empty."""
    async with async_session() as session:
        count = await session.scalar(select(func.count()).select_from(QuestionDB))
        if count and count > 0:
            logger.info(f"Database already has {count} questions. Skipping seed.")
            return

        logger.info("Seeding database with questions...")
        questions_dir = Path(__file__).parent.parent / "data" / "questions"
        if not questions_dir.exists():
            logger.warning(f"Questions directory not found: {questions_dir}")
            return

        total_imported = 0
        for json_file in questions_dir.glob("*.json"):
            logger.info(f"Loading {json_file.name}...")
            with open(json_file) as f:
                data = json.load(f)

            questions = data if isinstance(data, list) else data.get("questions", [])
            for q in questions:
                try:
                    db_question = QuestionDB(
                        subject=q["subject"],
                        question_type=q["question_type"],
                        format=q.get("format", "multiple_choice"),
                        difficulty=q.get("difficulty", 3),
                        content=json.dumps(q.get("content", {})),
                        answer=json.dumps(q.get("answer", {})),
                        explanation=q.get("explanation", ""),
                        hints=json.dumps(q.get("hints", [])),
                        tags=json.dumps(q.get("tags", [])),
                        source=q.get("source"),
                    )
                    session.add(db_question)
                    total_imported += 1
                except Exception as e:
                    logger.error(f"Error importing question: {e}")

            await session.commit()

        logger.info(f"Imported {total_imported} questions.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized.")

    # Seed questions if database is empty
    await seed_questions()

    # Ensure data directories exist
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.questions_dir.mkdir(parents=True, exist_ok=True)
    settings.materials_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Startup complete.")
    yield

    # Shutdown (cleanup if needed)
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.app_name,
    description="AI-powered 11+ exam preparation platform for GL Assessment",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "https://deep-tutor.pages.dev",
        "https://*.pages.dev",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(questions_router)
app.include_router(practice_router)
app.include_router(progress_router)
app.include_router(users_router)

# Mount static files for images
images_dir = Path(__file__).parent.parent / "data" / "images"
if images_dir.exists():
    app.mount("/images", StaticFiles(directory=str(images_dir)), name="images")


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "description": "11+ exam preparation for GL Assessment",
        "subjects": ["english", "maths", "verbal_reasoning", "non_verbal_reasoning"],
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
