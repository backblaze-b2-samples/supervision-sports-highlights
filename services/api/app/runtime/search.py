from fastapi import APIRouter

from app.service import search as search_service
from app.types import SearchHit

router = APIRouter()


@router.get("/search", response_model=list[SearchHit])
async def search_endpoint(q: str = "", limit: int = 50):
    limit = max(1, min(limit, 200))
    return search_service.search(q, limit=limit)
