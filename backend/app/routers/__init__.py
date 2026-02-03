from .questions import router as questions_router
from .practice import router as practice_router
from .users import router as users_router
from .visualize import router as visualize_router
from .research import router as research_router
from .generator import router as generator_router
from .lessons import router as lessons_router

__all__ = [
    "questions_router",
    "practice_router",
    "users_router",
    "visualize_router",
    "research_router",
    "generator_router",
    "lessons_router",
]
