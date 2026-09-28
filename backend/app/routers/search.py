from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Link, ProcessingStatus, Summary
from app.schemas import LinkRead, SearchResult
from app.services.embeddings import embed

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=list[SearchResult])
async def search(
    q: str = Query(min_length=2),
    limit: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> list[SearchResult]:
    """Recherche sémantique : similarité cosinus entre la requête et les résumés."""
    vector = await embed(q)
    distance = Summary.embedding.cosine_distance(vector).label("distance")

    stmt = (
        select(Link, distance)
        .join(Summary, Summary.link_id == Link.id)
        .where(Link.status == ProcessingStatus.done)
        .order_by(distance)
        .limit(limit)
    )

    return [
        SearchResult(link=LinkRead.model_validate(link), score=1 - row_distance)
        for link, row_distance in await session.execute(stmt)
    ]
