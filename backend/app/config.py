from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://cerebro:cerebro@localhost:5432/cerebro"
    # Facultative : la clé peut aussi être collée dans l'interface (voir
    # `services/openai_key.py`).
    openai_api_key: str | None = None

    transcription_model: str = "gpt-transcribe"
    # Langues attendues dans l'audio. Les vidéos suivies sont francophones et
    # truffées d'anglais technique : annoncer les deux évite que le modèle
    # tranche pour l'une et translittère l'autre.
    transcription_languages: list[str] = ["fr", "en"]
    summary_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    media_dir: Path = Path("/tmp/cerebro")
    max_chunk_mb: int = 24
    # Plafond de durée par morceau, en plus du plafond de taille. Le second ne
    # suffit pas : 24 Mo valent ~37 min à 85 kbps, mais bien plus d'une heure
    # sur un audio peu dense — la taille ne borne donc pas la durée.
    # 35 min se place juste au-dessus des 32,5 min vérifiées intactes, pour ne
    # pas couper en pleine phrase ce qui passe déjà d'un seul tenant.
    max_chunk_seconds: int = 2100
    subprocess_timeout: int = 1800
    max_transcript_chars: int = 400_000

    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
