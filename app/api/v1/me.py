"""The signed-in user."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import CurrentUserDep

router = APIRouter(tags=["auth"])


class Me(BaseModel):
    sub: str
    email: str


@router.get("/me", response_model=Me, summary="The signed-in user")
async def me(user: CurrentUserDep) -> Me:
    return Me(sub=user.sub, email=user.email)
