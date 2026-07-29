from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.providers.llm import LLMProvider, get_llm_provider


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    x_device_id: Annotated[str | None, Header(alias="X-Device-Id")] = None,
) -> User:
    if not x_device_id or not x_device_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Device-Id header",
        )
    device_id = x_device_id.strip()
    result = await db.execute(select(User).where(User.device_id == device_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(device_id=device_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


def provide_llm() -> LLMProvider:
    return get_llm_provider()


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
LLM = Annotated[LLMProvider, Depends(provide_llm)]
