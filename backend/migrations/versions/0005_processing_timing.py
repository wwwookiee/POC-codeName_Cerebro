"""Enregistre le minutage des traitements

Rien ne mesurait la durée d'un traitement, donc rien ne permettait d'en estimer
un nouveau. Trois colonnes le rendent possible : le début du traitement en
cours, sa durée une fois réussi, et la durée de l'audio.

`created_at` ne pouvait pas servir de départ : sur une relance il date de
l'ajout du lien, et le compteur afficherait des jours.

Toutes nullables : les liens déjà traités n'ont aucune de ces valeurs, et
aucune ne se reconstitue après coup. Ils restent simplement hors de
l'historique servant aux estimations, qui se remplit au fil des traitements
suivants.

Revision ID: 0005_processing_timing
Revises: 0004_link_creator
Create Date: 2026-09-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_processing_timing"
down_revision: str | None = "0004_link_creator"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "links",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("links", sa.Column("processing_seconds", sa.Float(), nullable=True))
    op.add_column("links", sa.Column("audio_seconds", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("links", "audio_seconds")
    op.drop_column("links", "processing_seconds")
    op.drop_column("links", "processing_started_at")
