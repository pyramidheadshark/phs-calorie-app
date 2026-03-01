"""initial_schema

Revision ID: 27ef6849b285
Revises:
Create Date: 2026-03-03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "27ef6849b285"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.Text(), nullable=True),
        sa.Column("first_name", sa.Text(), nullable=True),
        sa.Column("settings", postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("telegram_id"),
    )

    op.create_table(
        "meal_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("logged_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("photo_path", sa.Text(), nullable=True),
        sa.Column("calories", sa.Integer(), nullable=True),
        sa.Column("protein_g", sa.Numeric(6, 1), nullable=True),
        sa.Column("fat_g", sa.Numeric(6, 1), nullable=True),
        sa.Column("carbs_g", sa.Numeric(6, 1), nullable=True),
        sa.Column("portion_g", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Text(), nullable=True),
        sa.Column("gemini_raw", postgresql.JSONB(), nullable=True),
        sa.Column("confirmed", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.telegram_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_meal_entries_user_date",
        "meal_entries",
        ["user_id", "logged_at"],
    )

    op.create_table(
        "water_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("logged_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("amount_ml", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.telegram_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_water_entries_user_date",
        "water_entries",
        ["user_id", "logged_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_water_entries_user_date", table_name="water_entries")
    op.drop_table("water_entries")
    op.drop_index("idx_meal_entries_user_date", table_name="meal_entries")
    op.drop_table("meal_entries")
    op.drop_table("users")
