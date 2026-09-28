"""Estimation de la durée d'un traitement.

`estimate_seconds` est une cascade à trois branches, de la plus informée à la
moins informée. `ProcessingStats` est un dataclass gelé : aucune base requise.
"""

import pytest

from app.services.estimation import (
    DEFAULT_ESTIMATE_SECONDS,
    ProcessingStats,
    estimate_seconds,
)


def test_le_ratio_l_emporte_quand_la_duree_audio_est_connue() -> None:
    stats = ProcessingStats(median_seconds=300.0, median_ratio=0.5)
    assert estimate_seconds(stats, 600.0) == 300.0


def test_replie_sur_la_mediane_sans_ratio() -> None:
    stats = ProcessingStats(median_seconds=240.0, median_ratio=None)
    assert estimate_seconds(stats, 600.0) == 240.0


@pytest.mark.parametrize("duree", [None, 0, -30.0])
def test_replie_sur_la_mediane_sans_duree_audio_exploitable(duree: float | None) -> None:
    # Le ratio est là, mais il n'y a rien à multiplier.
    stats = ProcessingStats(median_seconds=240.0, median_ratio=0.5)
    assert estimate_seconds(stats, duree) == 240.0


@pytest.mark.parametrize("duree", [None, 600.0])
def test_replie_sur_le_defaut_quand_l_historique_est_vide(duree: float | None) -> None:
    stats = ProcessingStats(median_seconds=None, median_ratio=None)
    assert estimate_seconds(stats, duree) == DEFAULT_ESTIMATE_SECONDS
