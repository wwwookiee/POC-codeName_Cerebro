"""Estime la durée d'un traitement à partir de ceux déjà effectués.

Deux niveaux, du plus grossier au plus juste :

1. la médiane des durées passées, disponible dès la seconde zéro ;
2. une fois l'audio téléchargé et sa durée connue, la médiane du rapport
   « secondes de traitement par seconde d'audio », appliquée à cette vidéo.

L'estimation se corrige donc en cours de route, ce qui est assumé : une vidéo
de dix minutes et une d'une heure n'ont pas le même coût, et le premier niveau
seul les annoncerait identiques.

La médiane plutôt que la moyenne : un unique traitement parti en timeout
réseau tirerait durablement une moyenne calculée sur si peu d'échantillons.
"""

from dataclasses import dataclass
from statistics import median

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Link, ProcessingStatus

# Repli tant que l'historique est trop mince pour dire quoi que ce soit. Ordre
# de grandeur d'un traitement observé, pas une promesse.
DEFAULT_ESTIMATE_SECONDS = 180.0

# En dessous, la médiane porte plus de bruit que de signal.
MIN_SAMPLES = 3


@dataclass(frozen=True)
class ProcessingStats:
    median_seconds: float | None
    """Médiane des durées de traitement réussies."""

    median_ratio: float | None
    """Médiane des secondes de traitement par seconde d'audio."""


async def processing_stats(session: AsyncSession) -> ProcessingStats:
    rows = (
        await session.execute(
            select(Link.processing_seconds, Link.audio_seconds).where(
                Link.status == ProcessingStatus.done,
                Link.processing_seconds.is_not(None),
            )
        )
    ).all()

    durations = [row.processing_seconds for row in rows if row.processing_seconds > 0]
    ratios = [
        row.processing_seconds / row.audio_seconds
        for row in rows
        if row.audio_seconds and row.audio_seconds > 0 and row.processing_seconds > 0
    ]

    return ProcessingStats(
        median_seconds=median(durations) if len(durations) >= MIN_SAMPLES else None,
        median_ratio=median(ratios) if len(ratios) >= MIN_SAMPLES else None,
    )


def estimate_seconds(stats: ProcessingStats, audio_seconds: float | None) -> float:
    """Estimation pour un traitement, la plus informée que l'historique permette."""
    if audio_seconds and audio_seconds > 0 and stats.median_ratio is not None:
        return audio_seconds * stats.median_ratio
    if stats.median_seconds is not None:
        return stats.median_seconds
    return DEFAULT_ESTIMATE_SECONDS
