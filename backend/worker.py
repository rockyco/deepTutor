"""Cloudflare Workers entry point for FastAPI app."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import routers
from app.routers import practice, questions, progress, users

app = FastAPI(
    title="11+ Deep Tutor API",
    description="Backend API for the 11+ exam practice tutor",
    version="1.0.0",
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://deeptutor.pages.dev",  # Cloudflare Pages default
        "http://localhost:3000",  # Local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(practice.router)
app.include_router(questions.router)
app.include_router(progress.router)
app.include_router(users.router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "11+ Deep Tutor API"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Cloudflare Workers handler
async def on_fetch(request, env):
    """Handle incoming requests from Cloudflare Workers."""
    import asgi

    return await asgi.fetch(app, request, env)
