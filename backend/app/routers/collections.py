from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Collection, link_collections
from app.schemas import CollectionCreate, CollectionRead, CollectionUpdate

router = APIRouter(prefix="/api/collections", tags=["collections"])


async def _link_counts(session: AsyncSession) -> dict[UUID, int]:
    stmt = select(link_collections.c.collection_id, func.count()).group_by(
        link_collections.c.collection_id
    )
    return {row[0]: row[1] for row in await session.execute(stmt)}


def _to_read(collection: Collection, counts: dict[UUID, int]) -> CollectionRead:
    return CollectionRead(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        created_at=collection.created_at,
        link_count=counts.get(collection.id, 0),
    )


async def _get_collection(session: AsyncSession, collection_id: UUID) -> Collection:
    collection = await session.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection introuvable")
    return collection


@router.post("", response_model=CollectionRead, status_code=status.HTTP_201_CREATED)
async def create_collection(
    payload: CollectionCreate, session: AsyncSession = Depends(get_session)
) -> CollectionRead:
    collection = Collection(name=payload.name.strip(), description=payload.description)
    session.add(collection)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Une collection porte déjà ce nom") from None

    await session.refresh(collection)
    return _to_read(collection, {})


@router.get("", response_model=list[CollectionRead])
async def list_collections(session: AsyncSession = Depends(get_session)) -> list[CollectionRead]:
    counts = await _link_counts(session)
    collections = await session.scalars(select(Collection).order_by(Collection.name))
    return [_to_read(collection, counts) for collection in collections]


@router.patch("/{collection_id}", response_model=CollectionRead)
async def update_collection(
    collection_id: UUID,
    payload: CollectionUpdate,
    session: AsyncSession = Depends(get_session),
) -> CollectionRead:
    collection = await _get_collection(session, collection_id)

    if payload.name is not None:
        collection.name = payload.name.strip()
    if payload.description is not None:
        collection.description = payload.description

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Une collection porte déjà ce nom") from None

    await session.refresh(collection)
    counts = await _link_counts(session)
    return _to_read(collection, counts)


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: UUID, session: AsyncSession = Depends(get_session)
) -> None:
    collection = await _get_collection(session, collection_id)
    await session.delete(collection)
    await session.commit()
