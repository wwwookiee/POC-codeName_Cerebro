"""Reconnaissance des URL YouTube.

`app/services/youtube.py` n'importe que la bibliothèque standard : c'est le seul
module du backend qui se teste sans même la clé factice posée par `conftest.py`.
"""

import pytest

from app.services.youtube import canonical_url, extract_video_id

ID = "NU2yHYXvJFY"


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={ID}",
        f"https://youtube.com/watch?v={ID}",
        f"https://m.youtube.com/watch?v={ID}",
        f"http://www.youtube.com/watch?v={ID}",
        f"https://youtu.be/{ID}",
        f"https://www.youtube.com/embed/{ID}",
        f"https://www.youtube.com/shorts/{ID}",
        f"https://www.youtube.com/live/{ID}",
        f"https://www.youtube.com/v/{ID}",
        f"https://music.youtube.com/watch?v={ID}",
        f"https://www.youtube-nocookie.com/embed/{ID}",
    ],
)
def test_formes_reconnues(url: str) -> None:
    assert extract_video_id(url) == ID


@pytest.mark.parametrize(
    "url",
    [
        # Les paramètres et fragments en trop ne doivent pas gêner : c'est sous
        # cette forme qu'une URL arrive quand elle est copiée depuis le lecteur.
        f"https://www.youtube.com/watch?v={ID}&list=PLabcdef&index=3",
        f"https://youtu.be/{ID}?t=42",
        f"https://youtu.be/{ID}/segment-en-trop",
        f"  https://www.youtube.com/watch?v={ID}  ",
    ],
)
def test_bruit_autour_de_l_identifiant(url: str) -> None:
    assert extract_video_id(url) == ID


@pytest.mark.parametrize(
    "url",
    [
        "https://vimeo.com/123456789",
        "https://exemple.fr/watch?v=" + ID,
        f"ftp://www.youtube.com/watch?v={ID}",
        "javascript:alert(1)",
        f"www.youtube.com/watch?v={ID}",  # sans schéma
        "https://www.youtube.com/watch",  # pas de paramètre v
        "https://www.youtube.com/watch?v=",
        "https://www.youtube.com/watch?v=trop-court",  # 10 caractères
        "https://www.youtube.com/watch?v=beaucoup-trop-long",
        "https://www.youtube.com/feed/subscriptions",
        "https://www.youtube.com/",
        "https://youtu.be/",
        "",
        "pas une url du tout",
    ],
)
def test_formes_rejetees(url: str) -> None:
    assert extract_video_id(url) is None


def test_aller_retour_par_l_url_canonique() -> None:
    assert extract_video_id(canonical_url(ID)) == ID
