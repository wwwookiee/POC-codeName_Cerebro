"""Texte soumis à l'embedding.

Ce qui entre ici détermine ce que la recherche sémantique saura rapprocher —
d'où la présence du créateur, pour qu'une requête formulée autour d'une chaîne
fonctionne.
"""

from app.services.embeddings import embedding_input
from app.services.pipeline import SummaryPayload


def _payload(**surcharges: object) -> SummaryPayload:
    defauts: dict[str, object] = {
        "suggested_title": "Titre suggéré",
        "short_summary": "Un résumé court.",
        "key_points": ["premier point", "second point"],
        "tags": ["python", "ia"],
        "complexity_level": "intermédiaire",
    }
    return SummaryPayload(**{**defauts, **surcharges})  # type: ignore[arg-type]


def test_assemble_toutes_les_parties_dans_l_ordre() -> None:
    texte = embedding_input(_payload(), "Titre de la vidéo", "Rudy IO")
    assert texte.split("\n") == [
        "Titre de la vidéo",
        "Rudy IO",
        "Titre suggéré",
        "Un résumé court.",
        "premier point second point",
        "python ia",
    ]


def test_le_createur_est_facultatif() -> None:
    texte = embedding_input(_payload(), "Titre de la vidéo")
    assert "Rudy IO" not in texte
    assert texte.startswith("Titre de la vidéo\nTitre suggéré")


def test_les_parties_vides_ne_laissent_pas_de_ligne_blanche() -> None:
    texte = embedding_input(
        _payload(suggested_title=None, key_points=[], tags=[]),
        "Titre de la vidéo",
    )
    assert texte == "Titre de la vidéo\nUn résumé court."
    assert "\n\n" not in texte


def test_un_resume_minimal_ne_laisse_pas_d_espaces_en_bord() -> None:
    texte = embedding_input(
        _payload(suggested_title=None, short_summary="", key_points=[], tags=[]),
        "Titre de la vidéo",
    )
    assert texte == "Titre de la vidéo"
