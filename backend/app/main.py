"""11+ Deep Tutor - FastAPI Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.routers import questions_router, practice_router, progress_router, users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()

    # Ensure data directories exist
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.questions_dir.mkdir(parents=True, exist_ok=True)
    settings.materials_dir.mkdir(parents=True, exist_ok=True)

    yield

    # Shutdown (cleanup if needed)


app = FastAPI(
    title=settings.app_name,
    description="AI-powered 11+ exam preparation platform for GL Assessment",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(questions_router)
app.include_router(practice_router)
app.include_router(progress_router)
app.include_router(users_router)


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
