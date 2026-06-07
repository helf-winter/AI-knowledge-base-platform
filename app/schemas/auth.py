from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    display_name: str
    roles: list[str] = Field(default_factory=list)


class CurrentUserRead(BaseModel):
    user_id: str
    username: str
    display_name: str
    email: str | None = None
    roles: list[str] = Field(default_factory=list)
