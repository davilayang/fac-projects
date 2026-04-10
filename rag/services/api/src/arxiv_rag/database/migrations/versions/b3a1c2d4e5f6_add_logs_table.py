"""add logs table

Revision ID: b3a1c2d4e5f6
Revises: 79d7c0279200
Create Date: 2026-04-08 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b3a1c2d4e5f6"
down_revision: str | None = "79d7c0279200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "logs",
        sa.Column(
            "id", sa.BigInteger(), autoincrement=True, nullable=False
        ),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "timestamp",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("level", sa.String(10), nullable=False),
        sa.Column("event", sa.Text(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("query", sa.Text(), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("tokens_input", sa.Integer(), nullable=True),
        sa.Column("tokens_output", sa.Integer(), nullable=True),
        sa.Column("chunks", postgresql.JSONB(), nullable=True),
        sa.Column("cited", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_logs_trace_id", "logs", ["trace_id"])
    op.create_index("ix_logs_timestamp", "logs", ["timestamp"])

    # Cleanup: delete logs older than 30 days
    # Run periodically via pg_cron or an external scheduler:
    # DELETE FROM logs WHERE timestamp < NOW() - INTERVAL '30 days';


def downgrade() -> None:
    op.drop_index("ix_logs_timestamp", table_name="logs")
    op.drop_index("ix_logs_trace_id", table_name="logs")
    op.drop_table("logs")
