from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.llm_generator import llm_service

router = APIRouter(prefix="/api/visualize", tags=["visualize"])

class VizRequest(BaseModel):
    topic: str

@router.post("/generate")
async def generate_visualization(req: VizRequest):
    """
    Generates Mermaid.js diagram code for the requested topic.
    """
    mermaid_code = await llm_service.generate_mermaid(req.topic)
    return {"mermaid": mermaid_code}

class TuitionRequest(BaseModel):
    question: str
    topic: str

@router.post("/tuition")
async def generate_tuition(req: TuitionRequest):
    """
    Generates interactive tuition (diagram + explanation) for a specific question.
    """
    return await llm_service.generate_tuition(req.question, req.topic)
