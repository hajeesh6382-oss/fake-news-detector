from typing import List, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel
from backend.services.news_search_service import search_cross_platform_news

router = APIRouter(prefix="/api", tags=["News Search"])

class SearchRequest(BaseModel):
    query: str
    max_results: int = 10

@router.post("/search")
async def search_news_endpoint(req: SearchRequest):
    """
    POST /api/search
    Searches Google News RSS, GDELT, and wire archives across platforms.
    """
    results = await search_cross_platform_news(
        headline=req.query,
        entities=[]
    )
    return {
        "query": req.query,
        "count": len(results[:req.max_results]),
        "results": results[:req.max_results]
    }
