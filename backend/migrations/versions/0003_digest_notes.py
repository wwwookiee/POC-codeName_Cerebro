"""Remplace le digest en prose par des notes structurées

La prose se relisait mal : on cherchait une information précise dans un pavé.
Le digest devient une suite de sections à puces, stockée en JSONB comme
`key_points` et `tags`.

Le contenu de `detailed_digest` n'est pas repris : la prose ne se découpe pas
en notes de façon fiable, et les digests concernés seront regénérés à la
prochaine ouverture de leur page.

Revision ID: 0003_digest_notes
Revises: 0002_detailed_digest
Create Date: 2026-09-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_digest_notes"
down_revision: str | None = "0002_detailed_digest"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "summaries",
        sa.Column("digest_notes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.drop_column("summaries", "detailed_digest")


def downgrade() -> None:
    op.add_column("summaries", sa.Column("detailed_digest", sa.Text(), nullable=True))
    op.drop_column("summaries", "digest_notes")
