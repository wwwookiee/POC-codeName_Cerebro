from fastapi import APIRouter, HTTPException, status
from openai import APIConnectionError, AsyncOpenAI, AuthenticationError

from app.config import settings
from app.schemas import OpenAIKeyStatus, OpenAIKeyUpdate
from app.services import openai_key

router = APIRouter(prefix="/api/settings/openai-key", tags=["settings"])


def _status() -> OpenAIKeyStatus:
    source = openai_key.key_source()
    if source is None:
        return OpenAIKeyStatus(configured=False, source=None, hint=None)
    return OpenAIKeyStatus(
        configured=True, source=source, hint=openai_key.masked(openai_key.current_key())
    )


@router.get("", response_model=OpenAIKeyStatus)
async def get_openai_key() -> OpenAIKeyStatus:
    """État de la clé, jamais la clé elle-même : seuls ses 4 derniers caractères sortent."""
    return _status()


@router.put("", response_model=OpenAIKeyStatus)
async def set_openai_key(payload: OpenAIKeyUpdate) -> OpenAIKeyStatus:
    """Vérifie la clé auprès d'OpenAI avant de la retenir.

    Une clé fausse retenue ne se révélerait qu'au premier traitement, après le
    téléchargement de l'audio : autant la refuser ici.
    """
    try:
        await AsyncOpenAI(api_key=payload.api_key).models.retrieve(settings.summary_model)
    except AuthenticationError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Clé refusée par OpenAI") from None
    except APIConnectionError:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "OpenAI injoignable") from None

    openai_key.set_runtime_key(payload.api_key)
    return _status()


@router.delete("", response_model=OpenAIKeyStatus)
async def clear_openai_key() -> OpenAIKeyStatus:
    """Oublie la clé collée ; le pipeline retombe sur `OPENAI_API_KEY` s'il y en a une."""
    openai_key.clear_runtime_key()
    return _status()
