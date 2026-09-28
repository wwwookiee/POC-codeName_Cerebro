"""Purge les notes pour qu'elles soient reprises avec le prompt corrigé

Les notes étaient plafonnées à 4-6 sections, ce qui écartait du contenu dès que
la vidéo énumérait plus d'éléments que de places disponibles : sur un top 8,
trois entrées disparaissaient purement et simplement. Le plafond est levé et
une règle d'exhaustivité ajoutée.

Elles sont mises en cache à la première ouverture et jamais recalculées : sans
cette purge, les notes déjà produites garderaient leur version tronquée et le
correctif resterait invisible là où il a été demandé.

Rien d'autre n'est touché. Les transcriptions restent en base, la régénération
ne coûte qu'un appel au modèle de résumé à la prochaine ouverture de chaque
page — ni téléchargement, ni transcription.

`downgrade` ne rend rien : des notes supprimées ne se reconstituent pas. C'est
sans conséquence, puisque c'est précisément ce que fait `upgrade`. La révision
0003 a assumé le même raisonnement pour la même raison.

Revision ID: 0006_reset_digest_notes
Revises: 0005_processing_timing
Create Date: 2026-09-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006_reset_digest_notes"
down_revision: str | None = "0005_processing_timing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE summaries SET digest_notes = NULL")


def downgrade() -> None:
    # Volontairement vide : voir l'en-tête.
    pass
