"""Clé OpenAI utilisée par le pipeline.

Pour un test local, la clé peut être collée dans l'interface plutôt que posée
dans `.env`. Elle ne vit alors qu'en mémoire du processus : jamais écrite en
base ni sur disque, elle disparaît au redémarrage du backend. Tant qu'elle est
posée, elle prime sur `OPENAI_API_KEY`.
"""

from typing import Literal

from app.config import settings

KeySource = Literal["interface", "env"]

_runtime_key: str | None = None


class MissingOpenAIKey(RuntimeError):
    def __init__(self) -> None:
        super().__init__(
            "Aucune clé OpenAI configurée : colle-la dans « Clé API » ou renseigne OPENAI_API_KEY"
        )


def set_runtime_key(key: str) -> None:
    global _runtime_key
    _runtime_key = key


def clear_runtime_key() -> None:
    global _runtime_key
    _runtime_key = None


def key_source() -> KeySource | None:
    if _runtime_key:
        return "interface"
    if settings.openai_api_key:
        return "env"
    return None


def current_key() -> str:
    key = _runtime_key or settings.openai_api_key
    if not key:
        raise MissingOpenAIKey()
    return key


def require_key() -> None:
    """Dépendance FastAPI : refuse d'amorcer un traitement voué à échouer.

    Sans elle, l'absence de clé ne se révélerait qu'après le téléchargement de
    l'audio, au premier appel au modèle.
    """
    current_key()


def masked(key: str) -> str:
    """Les 4 derniers caractères suffisent à reconnaître une clé sans l'exposer."""
    return f"…{key[-4:]}"
