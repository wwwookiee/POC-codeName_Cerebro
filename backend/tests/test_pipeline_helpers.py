"""Fonctions pures du pipeline.

Elles figent les décisions prises pendant les mesures : le plafond de 60 termes,
le plancher de 40 mots/min, le plafond de 2 000 tokens de sortie. Aucune ne
touche au réseau, à la base ni à ffmpeg.
"""

import json
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.config import settings
from app.services.pipeline import (
    MIN_WORDS_PER_MINUTE,
    PipelineError,
    _clean_creator,
    _decode_description,
    _sections,
    _str_list,
    _warn_if_token_capped,
    extract_keywords,
    looks_truncated,
    split_audio,
)


class TestExtractKeywords:
    def test_retire_les_url_avant_d_extraire(self) -> None:
        termes = extract_keywords("Voir https://github.com/Foo/Bar pour DeepSeek Harness")
        assert "DeepSeek Harness" in termes
        # Les fragments capitalisés d'une URL sont du bruit, pas des noms cités.
        assert not any("Foo" in terme or "Bar" in terme for terme in termes)

    def test_ecarte_les_termes_de_moins_de_trois_caracteres(self) -> None:
        assert extract_keywords("AI\nGPT") == ["GPT"]

    def test_ecarte_un_terme_interminable(self) -> None:
        # Une ligne entièrement capitalisée s'agrège en un seul terme : voulu
        # pour « DeepSeek Harness », absurde au-delà de 60 caractères.
        ligne = " ".join(["Mot"] * 20)
        assert len(ligne) > 60
        assert extract_keywords(ligne) == []

    def test_deduplique_sans_tenir_compte_de_la_casse(self) -> None:
        # La première graphie rencontrée est celle qui est conservée.
        assert extract_keywords("Docker\nDOCKER") == ["Docker"]

    def test_plafonne_a_soixante_termes(self) -> None:
        # Séparés par des sauts de ligne : sur une même ligne ils fusionneraient.
        source = "\n".join(f"Terme{i}" for i in range(80))
        assert len(extract_keywords(source)) == 60

    def test_parcourt_les_sources_dans_l_ordre(self) -> None:
        assert extract_keywords("Alpha", "Beta") == ["Alpha", "Beta"]


class TestLooksTruncated:
    @pytest.mark.parametrize("duree", [None, 0, -12.0])
    def test_sans_duree_exploitable_ne_conclut_rien(self, duree: float | None) -> None:
        assert looks_truncated("un mot", duree) is False

    def test_signale_un_debit_sous_le_plancher(self) -> None:
        # 100 mots sur 10 minutes, soit 10 mots/min.
        assert looks_truncated("mot " * 100, 600) is True

    def test_laisse_passer_un_debit_normal(self) -> None:
        # 1 000 mots sur 10 minutes, soit 100 mots/min.
        assert looks_truncated("mot " * 1000, 600) is False

    def test_le_plancher_lui_meme_ne_declenche_pas(self) -> None:
        # Exactement 40 mots/min : la comparaison est stricte.
        mots = int(MIN_WORDS_PER_MINUTE * 10)
        assert looks_truncated("mot " * mots, 600) is False


class TestDecodeDescription:
    def test_decode_une_chaine_json(self) -> None:
        assert _decode_description(json.dumps("Une description\navec un saut")) == (
            "Une description\navec un saut"
        )

    @pytest.mark.parametrize("brut", ["pas du json", "123", "null", "[1, 2]", ""])
    def test_tout_le_reste_vaut_chaine_vide(self, brut: str) -> None:
        # Une description illisible ne coûte que des termes en moins : elle n'a
        # pas à faire échouer un traitement déjà payé.
        assert _decode_description(brut) == ""


class TestCleanCreator:
    def test_retire_les_espaces(self) -> None:
        assert _clean_creator("  Rudy IO  ") == "Rudy IO"

    @pytest.mark.parametrize("brut", ["", "   ", "NA"])
    def test_absence_et_litteral_na_valent_none(self, brut: str) -> None:
        assert _clean_creator(brut) is None

    def test_na_n_est_filtre_qu_a_l_identique(self) -> None:
        assert _clean_creator("NASA") == "NASA"


class TestStrList:
    def test_convertit_chaque_element(self) -> None:
        assert _str_list([1, "deux", 3.0]) == ["1", "deux", "3.0"]

    @pytest.mark.parametrize("valeur", ["une chaine", None, 42, {"a": 1}])
    def test_ce_qui_n_est_pas_une_liste_vaut_liste_vide(self, valeur: object) -> None:
        assert _str_list(valeur) == []


class TestSections:
    def test_garde_une_section_complete_et_nettoie_les_espaces(self) -> None:
        brut = [{"titre": "  Un titre  ", "puces": ["  une puce  ", "une autre"]}]
        assert _sections(brut) == [{"titre": "Un titre", "puces": ["une puce", "une autre"]}]

    @pytest.mark.parametrize(
        "item",
        [
            {"titre": "", "puces": ["une puce"]},
            {"titre": "   ", "puces": ["une puce"]},
            {"titre": "Un titre", "puces": []},
            {"titre": "Un titre", "puces": ["   "]},
            {"titre": "Un titre"},
            "pas un dictionnaire",
        ],
    )
    def test_ecarte_une_section_inexploitable(self, item: object) -> None:
        assert _sections([item]) == []

    @pytest.mark.parametrize("brut", ["", None, {"titre": "x"}])
    def test_ce_qui_n_est_pas_une_liste_vaut_liste_vide(self, brut: object) -> None:
        assert _sections(brut) == []


class TestWarnIfTokenCapped:
    def _transcript(self, produits: object) -> SimpleNamespace:
        return SimpleNamespace(usage=SimpleNamespace(output_tokens=produits))

    def test_avertit_au_plafond(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            _warn_if_token_capped(Path("morceau.mp3"), self._transcript(2000))
        assert "morceau.mp3" in caplog.text
        assert "tronqué" in caplog.text

    def test_reste_silencieux_juste_en_dessous(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            _warn_if_token_capped(Path("morceau.mp3"), self._transcript(1999))
        assert caplog.text == ""

    @pytest.mark.parametrize(
        "transcript",
        [
            SimpleNamespace(),  # pas de champ usage
            SimpleNamespace(usage=None),
            SimpleNamespace(usage=SimpleNamespace(output_tokens=None)),
            "une transcription nue",  # le modèle nominal ne renvoie que du texte
        ],
    )
    def test_un_usage_absent_n_est_pas_une_troncature(
        self, transcript: object, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING):
            _warn_if_token_capped(Path("morceau.mp3"), transcript)
        assert caplog.text == ""


class TestSplitAudio:
    """Seul le chemin de sortie anticipée est couvert : le reste appelle ffmpeg."""

    async def test_un_fichier_court_et_leger_part_d_un_seul_tenant(self, tmp_path: Path) -> None:
        audio = tmp_path / "court.mp3"
        audio.write_bytes(b"\x00" * 1024)
        # Pile au plafond de durée : ceil(2100 / 2100) == 1, donc pas de découpe.
        assert await split_audio(audio, float(settings.max_chunk_seconds)) == [audio]

    async def test_une_sonde_en_echec_degrade_sans_interrompre(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        audio = tmp_path / "duree-illisible.mp3"
        audio.write_bytes(b"\x00" * 1024)

        async def sonde_en_echec(_: Path) -> float:
            raise PipelineError("ffprobe indisponible")

        monkeypatch.setattr("app.services.pipeline.duration_seconds", sonde_en_echec)
        with caplog.at_level(logging.WARNING):
            assert await split_audio(audio) == [audio]
        assert "duree-illisible.mp3" in caplog.text

    async def test_une_sonde_en_echec_sur_un_fichier_trop_gros_remonte(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        audio = tmp_path / "gros.mp3"
        audio.write_bytes(b"\x00" * 16)

        async def sonde_en_echec(_: Path) -> float:
            raise PipelineError("ffprobe indisponible")

        monkeypatch.setattr("app.services.pipeline.duration_seconds", sonde_en_echec)
        # Sans durée et au-dessus de la limite de taille, il n'y a pas d'issue :
        # on ne sait pas où couper.
        monkeypatch.setattr(settings, "max_chunk_mb", 0)
        with pytest.raises(PipelineError):
            await split_audio(audio)
