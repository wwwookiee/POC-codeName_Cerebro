"""Ajoute le créateur de la vidéo sur les liens

La chaîne n'était capturée nulle part : `download_audio` ne demandait à yt-dlp
que le titre et le chemin du fichier. La colonne alimente le premier tag de la
card, et entre dans le texte embeddé pour rendre « la vidéo de tel youtubeur »
trouvable par la recherche sémantique.

Nullable : les liens traités avant cette révision n'ont pas de créateur, et
aucune valeur par défaut n'aurait de sens. Ils se rattrapent avec
`python -m app.backfill_creator`, qui lit les métadonnées yt-dlp — gratuites —
et ré-embedde au passage, puisque le texte embeddé change de composition.

Revision ID: 0004_link_creator
Revises: 0003_digest_notes
Create Date: 2026-09-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_link_creator"
down_revision: str | None = "0003_digest_notes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("links", sa.Column("creator", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("links", "creator")
