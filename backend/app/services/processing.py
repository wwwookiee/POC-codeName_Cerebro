import logging
import shutil
from datetime import UTC, datetime
from uuid import UUID

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Link, ProcessingStatus, Summary
from app.services import pipeline
from app.services.embeddings import embed, embedding_input

logger = logging.getLogger(__name__)


async def process_link(link_id: UUID) -> None:
    """Exécute le pipeline complet pour un lien et persiste le résultat."""
    workdir = settings.media_dir / str(link_id)

    async with AsyncSessionLocal() as session:
        link = await session.get(Link, link_id)
        if link is None:
            return

        started = datetime.now(UTC)
        link.status = ProcessingStatus.processing
        link.error_message = None
        link.processing_started_at = started
        # Une relance repart de zéro : les mesures du passage précédent ne
        # décrivent plus celui qui commence.
        link.processing_seconds = None
        link.audio_seconds = None
        await session.commit()

        try:
            audio = await pipeline.download_audio(link.url, workdir)

            # Dès que la durée de l'audio est connue, elle est publiée : c'est
            # elle qui fait passer l'estimation de la médiane globale au calcul
            # propre à cette vidéo, pendant que le traitement continue.
            # Gardée en local : le rollback du cas d'échec expire l'instance, et
            # la durée est encore nécessaire au découpage comme au contrôle.
            audio_seconds: float | None = None
            try:
                audio_seconds = await pipeline.duration_seconds(audio.path)
                link.audio_seconds = audio_seconds
                await session.commit()
            except pipeline.PipelineError:
                # Une sonde de durée en échec ne coûte qu'une estimation moins
                # fine — elle n'a pas à faire échouer le traitement.
                logger.warning("Durée de l'audio illisible pour %s", link_id)
                await session.rollback()

            chunks = await pipeline.split_audio(audio.path, audio_seconds)
            transcript = await pipeline.transcribe(chunks, audio)

            # Une transcription trop courte pour la durée de l'audio signale une
            # troncature : le résumé serait produit sur un texte amputé, sans
            # que rien ne le signale. On journalise plutôt que d'échouer — une
            # vidéo peu bavarde donne légitimement peu de mots.
            if pipeline.looks_truncated(transcript, audio_seconds):
                logger.warning(
                    "Transcription anormalement courte pour %s : %d mots pour %.0f s d'audio",
                    link_id,
                    len(transcript.split()),
                    audio_seconds or 0,
                )
            payload = await pipeline.summarize(transcript)
            vector = await embed(embedding_input(payload, audio.title, audio.creator))

            link.title = audio.title
            link.creator = audio.creator
            link.status = ProcessingStatus.done
            link.processing_seconds = (datetime.now(UTC) - started).total_seconds()
            link.summary = Summary(
                suggested_title=payload.suggested_title,
                short_summary=payload.short_summary,
                key_points=payload.key_points,
                tags=payload.tags,
                complexity_level=payload.complexity_level,
                transcript=transcript,
                embedding=vector,
            )
            await session.commit()
        except Exception as exc:
            logger.exception("Échec du traitement du lien %s", link_id)
            await session.rollback()
            link = await session.get(Link, link_id)
            if link is not None:
                link.status = ProcessingStatus.error
                link.error_message = f"{type(exc).__name__}: {exc}"[:1000]
                await session.commit()
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
