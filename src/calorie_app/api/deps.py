from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from calorie_app.adapters.db.repos import UserRepo
from calorie_app.adapters.db.session import get_session
from calorie_app.adapters.telegram import validate_init_data
from calorie_app.core.domain import User


async def get_db(session: AsyncSession = Depends(get_session)) -> AsyncGenerator[AsyncSession, None]:
    yield session


async def get_current_user(
    x_telegram_init_data: str = Header(..., alias="x-telegram-init-data"),
    session: AsyncSession = Depends(get_session),
) -> User:
    try:
        user_data = validate_init_data(x_telegram_init_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e

    telegram_id = int(user_data["id"])
    repo = UserRepo(session)
    user = await repo.get(telegram_id)

    if user is None:
        from calorie_app.core.domain import User as DomainUser

        new_user = DomainUser(
            telegram_id=telegram_id,
            username=user_data.get("username"),
            first_name=user_data.get("first_name"),
        )
        user = await repo.upsert(new_user)

    return user
