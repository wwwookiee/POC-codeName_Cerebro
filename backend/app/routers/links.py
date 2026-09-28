from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import Collection, Link, ProcessingStatus, Summary
from app.schemas import DigestRead, LinkCollectionsUpdate, LinkCreate, LinkDetail, LinkRead
from app.services import openai_key, pipeline
from app.services.estimation import estimate_seconds, processing_stats
from app.services.processing import process_link

router = APIRouter(prefix="/api/links", tags=["links"])


_RUNNING = (ProcessingStatus.pending, ProcessingStatus.processing)


async def _with_estimates(session: AsyncSession, links: list[Link]) -> list[Link]:
    """Attache l'estimation aux liens en cours, et à eux seuls.

    `estimated_seconds` n'est pas une colonne : elle se déduit de l'historique
    des traitements. Elle est posée sur l'instance, d'où le schéma la relit.
    Les statistiques ne sont calculées que s'il y a un lien à estimer.
    """
    running = [link for link in links if link.status in _RUNNING]
    if not running:
        return links

    stats = await processing_stats(session)
    for link in running:
        link.estimated_seconds = estimate_seconds(stats, link.audio_seconds)
    return links


async def _get_link(session: AsyncSession, link_id: UUID) -> Link:
    link = await session.get(Link, link_id)
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lien introuvable")
    return link


async def _get_link_with_summary(session: AsyncSession, link_id: UUID) -> Link:
    """Charge un lien avec son résumé, colonnes différées comprises."""
    stmt = (
        select(Link)
        .where(Link.id == link_id)
        .options(
            selectinload(Link.summary)
            .undefer(Summary.transcript)
            .undefer(Summary.digest_notes)
        )
    )
    link = await session.scalar(stmt)
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lien introuvable")
    return link


@router.post(
    "",
    response_model=LinkRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(openai_key.require_key)],
)
async def create_link(
    payload: LinkCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> Link:
    link = Link(url=payload.url, source="youtube")
    session.add(link)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Ce lien a déjà été ajouté") from None

    await session.refresh(link)

    background_tasks.add_task(process_link, link.id)
    await _with_estimates(session, [link])
    return link


@router.get("", response_model=list[LinkRead])
async def list_links(
    collection_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[Link]:
    stmt = select(Link).order_by(Link.created_at.desc())
    if collection_id is not None:
        stmt = stmt.where(Link.collections.any(Collection.id == collection_id))

    return await _with_estimates(session, list(await session.scalars(stmt)))


@router.get("/{link_id}", response_model=LinkDetail)
async def get_link(link_id: UUID, session: AsyncSession = Depends(get_session)) -> Link:
    link = await _get_link_with_summary(session, link_id)
    await _with_estimates(session, [link])
    return link


@router.post("/{link_id}/digest", response_model=DigestRead)
async def generate_link_digest(
    link_id: UUID, session: AsyncSession = Depends(get_session)
) -> DigestRead:
    """Rend les notes du lien, en les générant au premier appel.

    Idempotent : une fois les notes en base, les appels suivants les relisent
    sans repasser par le modèle.
    """
    link = await _get_link_with_summary(session, link_id)
    if link.summary is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ce lien n'a pas encore été résumé")

    if not link.summary.digest_notes:
        try:
            link.summary.digest_notes = await pipeline.generate_digest(
                link.summary.transcript, link.title
            )
        except pipeline.PipelineError as exc:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
        await session.commit()

    return DigestRead(digest_notes=link.summary.digest_notes)


@router.put("/{link_id}/collections", response_model=LinkRead)
async def set_link_collections(
    link_id: UUID,
    payload: LinkCollectionsUpdate,
    session: AsyncSession = Depends(get_session),
) -> Link:
    link = await _get_link(session, link_id)

    collections: list[Collection] = []
    if payload.collection_ids:
        found = list(
            await session.scalars(
                select(Collection).where(Collection.id.in_(payload.collection_ids))
            )
        )
        if len(found) != len(set(payload.collection_ids)):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection introuvable")
        collections = found

    link.collections = collections
    await session.commit()
    await session.refresh(link)
    await _with_estimates(session, [link])
    return link


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(link_id: UUID, session: AsyncSession = Depends(get_session)) -> None:
    link = await _get_link(session, link_id)
    await session.delete(link)
    await session.commit()


@router.post(
    "/{link_id}/retry",
    response_model=LinkRead,
    dependencies=[Depends(openai_key.require_key)],
)
async def retry_link(
    link_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> Link:
    link = await _get_link(session, link_id)
    if link.status != ProcessingStatus.error:
        raise HTTPException(status.HTTP_409_CONFLICT, "Seuls les liens en erreur peuvent être relancés")

    link.status = ProcessingStatus.pending
    link.error_message = None
    await session.commit()
    await session.refresh(link)

    background_tasks.add_task(process_link, link.id)
    await _with_estimates(session, [link])
    return link
