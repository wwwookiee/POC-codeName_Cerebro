from app.config import settings
from app.services.pipeline import SummaryPayload, openai_client


def embedding_input(
    payload: SummaryPayload, video_title: str, creator: str | None = None
) -> str:
    """Texte embeddé : de quoi parle la vidéo, sans la transcription brute.

    Le créateur en fait partie pour qu'une recherche formulée autour d'une
    chaîne (« la vidéo de tel youtubeur ») rapproche ses vidéos.
    """
    parts = [
        video_title,
        creator or "",
        payload.suggested_title or "",
        payload.short_summary,
        " ".join(payload.key_points),
        " ".join(payload.tags),
    ]
    return "\n".join(part for part in parts if part).strip()


async def embed(text: str) -> list[float]:
    client = openai_client()
    response = await client.embeddings.create(model=settings.embedding_model, input=text)
    return response.data[0].embedding
