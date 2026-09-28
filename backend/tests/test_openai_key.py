import pytest

from app.config import settings
from app.services import openai_key
from app.services.pipeline import openai_client


@pytest.fixture(autouse=True)
def reset_runtime_key():
    openai_key.clear_runtime_key()
    yield
    openai_key.clear_runtime_key()


def test_env_key_is_used_by_default():
    assert openai_key.key_source() == "env"
    assert openai_key.current_key() == settings.openai_api_key


def test_pasted_key_takes_precedence_over_env():
    openai_key.set_runtime_key("sk-collee-dans-l-interface-1234")

    assert openai_key.key_source() == "interface"
    assert openai_client().api_key == "sk-collee-dans-l-interface-1234"


def test_clearing_falls_back_to_env():
    openai_key.set_runtime_key("sk-collee-dans-l-interface-1234")
    openai_key.clear_runtime_key()

    assert openai_client().api_key == settings.openai_api_key


def test_missing_key_raises(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", None)

    assert openai_key.key_source() is None
    with pytest.raises(openai_key.MissingOpenAIKey):
        openai_client()


def test_empty_env_key_counts_as_missing(monkeypatch):
    # docker compose passe `OPENAI_API_KEY=` quand la variable n'est pas définie.
    monkeypatch.setattr(settings, "openai_api_key", "")

    assert openai_key.key_source() is None


def test_masked_shows_only_last_four():
    assert openai_key.masked("sk-proj-abcdefgh1234") == "…1234"
