from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    settings: Mapped[dict] = mapped_column(JSONB, server_default="{}")  # type: ignore[type-arg]
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class MealEntryModel(Base):
    __tablename__ = "meal_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False
    )
    logged_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    photo_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protein_g: Mapped[float | None] = mapped_column(Numeric(6, 1), nullable=True)
    fat_g: Mapped[float | None] = mapped_column(Numeric(6, 1), nullable=True)
    carbs_g: Mapped[float | None] = mapped_column(Numeric(6, 1), nullable=True)
    portion_g: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    gemini_raw: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # type: ignore[type-arg]
    confirmed: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )


class RecipeModel(Base):
    __tablename__ = "recipe_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, server_default="")
    ingredients: Mapped[list] = mapped_column(JSONB, server_default="[]")  # type: ignore[type-arg]
    instructions: Mapped[list] = mapped_column(JSONB, server_default="[]")  # type: ignore[type-arg]
    nutrition_estimate: Mapped[dict] = mapped_column(JSONB, server_default="{}")  # type: ignore[type-arg]
    cooking_time_min: Mapped[int] = mapped_column(Integer, server_default="30")
    equipment_used: Mapped[list] = mapped_column(JSONB, server_default="[]")  # type: ignore[type-arg]
    liked: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
