from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    employee_no: str | None = Field(default=None, min_length=1, max_length=64)
    username: str | None = Field(default=None, min_length=1, max_length=64)
    password: str = Field(min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    display_name: str = Field(min_length=1, max_length=128)
    email: str | None = Field(default=None, max_length=255)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    employee_no: str | None = None
    display_name: str
    department: str | None = None
    position: str | None = None
    permission_level: int = 1
    is_first_login: bool = False
    status: str = "active"
    roles: list[str] = Field(default_factory=list)


class CurrentUserRead(BaseModel):
    user_id: str
    username: str
    employee_no: str | None = None
    display_name: str
    email: str | None = None
    department: str | None = None
    position: str | None = None
    permission_level: int = 1
    is_first_login: bool = False
    status: str = "active"
    roles: list[str] = Field(default_factory=list)


class ChangeInitialPasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class VerifyPasswordRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)
