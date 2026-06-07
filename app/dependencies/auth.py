from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.auth import AuthService, AuthenticatedUser


def get_current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> AuthenticatedUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing token")

    token = authorization.split(" ", 1)[1].strip()
    auth = AuthService(db)
    try:
        return auth.get_current_user(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def require_roles(*roles: str):
    def _dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if roles and not any(role in user.roles for role in roles):
            raise HTTPException(status_code=403, detail="forbidden")
        return user

    return _dependency
