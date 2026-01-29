from fastapi import APIRouter
from pydantic import BaseModel
from app.services.llm_generator import llm_service

router = APIRouter(prefix="/generator", tags=["generator"])

class QuizRequest(BaseModel):
    topic: str
    difficulty: str = "Medium"

@router.post("/quiz")
async def generate_quiz(req: QuizRequest):
    """
    Generates a list of multiple choice questions.
    """
    questions = await llm_service.generate_quiz(req.topic, req.difficulty)
    return {"questions": questions}
