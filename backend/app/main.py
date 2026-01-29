"""11+ Deep Tutor - FastAPI Application."""

import json
import logging
import os
from contextlib import asynccontextmanager
import os
import base64
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func

from app.config import settings
from app.db import init_db
from app.db.database import async_session
from app.db.models import QuestionDB
from app.routers import (
    questions_router,
    practice_router,
    progress,
    users_router,
    visualize_router,
#     research_router,
#     generator_router,
)
from app.api import auth

logger = logging.getLogger(__name__)


async def seed_questions():
    """Seed database with questions from JSON files if empty."""
    async with async_session() as session:
        if os.getenv("SKIP_SEEDING", "").lower() == "true":
            logger.info("SKIP_SEEDING is set. Skipping database seed.")
            return

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
        "https://deeptutor.pages.dev",
        "https://deeptutor-frontend.pages.dev",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(questions_router)
app.include_router(practice_router)
app.include_router(progress.router, prefix="/api/progress", tags=["progress"])
app.include_router(visualize_router)
# app.include_router(research_router)
# app.include_router(generator_router)
app.include_router(auth.router, prefix="/api")

# Dev/Temp endpoint for image ingestion
class ImageUpload(BaseModel):
    filename: str
    content_b64: str

@app.post("/api/dev/upload_image")
async def upload_image(data: ImageUpload):
    # Save to standard images dir
    output_dir = "data/images/granular_non_verbal_reasoning"
    os.makedirs(output_dir, exist_ok=True)
    
    file_path = os.path.join(output_dir, data.filename)
    
    # Handle data URI prefix
    content = data.content_b64
    if "base64," in content:
        content = content.split("base64,")[1]
        
    with open(file_path, "wb") as f:
        f.write(base64.b64decode(content))
        
    return {"status": "ok", "path": f"/images/granular_non_verbal_reasoning/{data.filename}"}

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
