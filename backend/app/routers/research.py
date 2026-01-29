from fastapi import APIRouter
from pydantic import BaseModel
from duckduckgo_search import DDGS
from app.services.llm_generator import llm_service

router = APIRouter(prefix="/research", tags=["research"])

class ResearchRequest(BaseModel):
    query: str

@router.post("/query")
async def research_topic(req: ResearchRequest):
    """
    Performs a web search and synthesizes an answer.
    """
    # 1. Search Web
    with DDGS() as ddgs:
        # Get top 5 results
        results = list(ddgs.text(req.query, max_results=5))
    
    # 2. Synthesize with LLM
    answer = await llm_service.synthesize_research(req.query, results)
    
    return {
        "answer": answer,
        "sources": results
    }
