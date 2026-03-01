"""add recipe_entries table

Revision ID: a1b2c3d4e5f6
Revises: 27ef6849b285
Create Date: 2026-01-29 12:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a1b2c3d4e5f6"
down_revision = "27ef6849b285"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recipe_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("ingredients", postgresql.JSONB(), server_default="[]"),
        sa.Column("instructions", postgresql.JSONB(), server_default="[]"),
        sa.Column("nutrition_estimate", postgresql.JSONB(), server_default="{}"),
        sa.Column("cooking_time_min", sa.Integer(), server_default="30"),
        sa.Column("equipment_used", postgresql.JSONB(), server_default="[]"),
        sa.Column("liked", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_recipe_entries_user_id", "recipe_entries", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_recipe_entries_user_id", table_name="recipe_entries")
    op.drop_table("recipe_entries")
