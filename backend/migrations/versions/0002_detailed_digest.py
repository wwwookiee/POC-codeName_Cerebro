"""Ajoute summaries.detailed_digest, le digest long généré à la demande

Revision ID: 0002_detailed_digest
Revises: 0001_baseline
Create Date: 2026-09-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_detailed_digest"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable : les résumés déjà en base n'ont pas de digest, il sera généré
    # au premier affichage de leur page de détail.
    op.add_column("summaries", sa.Column("detailed_digest", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("summaries", "detailed_digest")
