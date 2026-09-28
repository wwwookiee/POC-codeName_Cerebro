"""Rattrape le créateur des liens traités avant l'ajout de la colonne.

`python -m app.backfill_creator [--dry-run]`

Pour chaque lien sans créateur, lit les métadonnées yt-dlp — sans téléchargement
ni transcription, donc sans coût — puis recalcule l'embedding, puisque le texte
embeddé inclut désormais la chaîne et que des vecteurs composés différemment ne
se comparent pas entre eux.

Idempotent : un lien qui a déjà un créateur est ignoré. Une vidéo devenue
indisponible est signalée et n'interrompt pas le reste du lot.
"""

import argparse
import asyncio
import logging

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Link, ProcessingStatus
from app.services.embeddings import embed, embedding_input
from app.services.pipeline import SummaryPayload, fetch_creator

logger = logging.getLogger("backfill_creator")


async def backfill(dry_run: bool = False) -> tuple[int, int]:
    """Retourne (liens complétés, liens en échec)."""
    completed = 0
    failed = 0

    async with AsyncSessionLocal() as session:
        links = (
            (
                await session.execute(
                    select(Link).where(
                        Link.creator.is_(None),
                        Link.status == ProcessingStatus.done,
                    )
                )
            )
            .scalars()
            .all()
        )

        if not links:
            logger.info("Aucun lien à compléter.")
            return 0, 0

        logger.info("%d lien(s) sans créateur.", len(links))

        for link in links:
            try:
                creator = await fetch_creator(link.url)
            except Exception as exc:
                logger.warning("%s : métadonnées illisibles (%s)", link.url, exc)
                failed += 1
                continue

            if creator is None:
                logger.warning("%s : yt-dlp ne renvoie pas de chaîne", link.url)
                failed += 1
                continue

            logger.info("%s -> %s%s", link.url, creator, " (dry-run)" if dry_run else "")
            if dry_run:
                completed += 1
                continue

            link.creator = creator

            # Le résumé est déjà en base : on ne régénère que le vecteur, à
            # partir du même payload augmenté du créateur.
            summary = link.summary
            if summary is not None:
                payload = SummaryPayload(
                    suggested_title=summary.suggested_title,
                    short_summary=summary.short_summary,
                    key_points=summary.key_points,
                    tags=summary.tags,
                    complexity_level=summary.complexity_level,
                )
                summary.embedding = await embed(
                    embedding_input(payload, link.title or "", creator)
                )

            await session.commit()
            completed += 1

    return completed, failed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="affiche ce qui serait écrit sans rien modifier",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    completed, failed = asyncio.run(backfill(dry_run=args.dry_run))
    logger.info("Terminé : %d complété(s), %d en échec.", completed, failed)


if __name__ == "__main__":
    main()
