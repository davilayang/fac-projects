"""create arxiv_chunks table

Revision ID: 79d7c0279200
Revises:
Create Date: 2026-04-06 14:17:40.430175

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "79d7c0279200"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "arxiv_chunks",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("arxiv_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("authors", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("published", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("categories", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("primary_category", sa.Text(), nullable=True),
        sa.Column("section", sa.Text(), nullable=True),
        sa.Column("subsection", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("idx_arxiv_chunks_arxiv_id", "arxiv_chunks", ["arxiv_id"])
    op.create_index(
        "idx_arxiv_chunks_primary_category", "arxiv_chunks", ["primary_category"]
    )
    op.create_index("idx_arxiv_chunks_published", "arxiv_chunks", ["published"])
    op.execute(
        "CREATE INDEX idx_arxiv_chunks_embedding ON arxiv_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_arxiv_chunks_embedding")
    op.drop_index("idx_arxiv_chunks_published", table_name="arxiv_chunks")
    op.drop_index("idx_arxiv_chunks_primary_category", table_name="arxiv_chunks")
    op.drop_index("idx_arxiv_chunks_arxiv_id", table_name="arxiv_chunks")
    op.drop_table("arxiv_chunks")
