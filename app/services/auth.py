from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import User, UserRole, Role, Department


@dataclass
class AuthenticatedUser:
    user_id: str
    username: str
    display_name: str
    email: str | None
    roles: list[str]


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        return hmac.compare_digest(self._hash_password(plain_password), password_hash)

    def seed_default_admin(self) -> None:
        department = self.db.execute(select(Department).where(Department.department_name == "平台管理部")).scalar_one_or_none()
        if department is None:
            department = Department(department_id=str(uuid.uuid4()), department_name="平台管理部")
            self.db.add(department)
            self.db.flush()

        admin_role = self.db.execute(select(Role).where(Role.role_name == "admin")).scalar_one_or_none()
        if admin_role is None:
            admin_role = Role(role_id=str(uuid.uuid4()), role_name="admin")
            self.db.add(admin_role)
            self.db.flush()

        user = self.db.execute(select(User).where(User.username == "admin")).scalar_one_or_none()
        if user is None:
            user = User(
                user_id=str(uuid.uuid4()),
                department_id=department.department_id,
                username="admin",
                display_name="系统管理员",
                email="admin@example.com",
                password_hash=self._hash_password("123456"),
                is_active=True,
            )
            self.db.add(user)
            self.db.flush()

        user_role = self.db.execute(
            select(UserRole).where(UserRole.user_id == user.user_id, UserRole.role_id == admin_role.role_id)
        ).scalar_one_or_none()
        if user_role is None:
            self.db.add(UserRole(user_id=user.user_id, role_id=admin_role.role_id))

        self.db.commit()

    def register(self, username: str, password: str, display_name: str, email: str | None = None) -> tuple[AuthenticatedUser, str]:
        existed = self.db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if existed is not None:
            raise ValueError("username already exists")

        department = self.db.execute(select(Department).where(Department.department_name == "普通用户")).scalar_one_or_none()
        if department is None:
            department = Department(department_id=str(uuid.uuid4()), department_name="普通用户")
            self.db.add(department)
            self.db.flush()

        user_role = self.db.execute(select(Role).where(Role.role_name == "user")).scalar_one_or_none()
        if user_role is None:
            user_role = Role(role_id=str(uuid.uuid4()), role_name="user")
            self.db.add(user_role)
            self.db.flush()

        user = User(
            user_id=str(uuid.uuid4()),
            department_id=department.department_id,
            username=username,
            display_name=display_name,
            email=email,
            password_hash=self._hash_password(password),
            is_active=True,
        )
        self.db.add(user)
        self.db.flush()
        self.db.add(UserRole(user_id=user.user_id, role_id=user_role.role_id))
        self.db.commit()

        auth_user = AuthenticatedUser(user_id=user.user_id, username=user.username, display_name=user.display_name, email=user.email, roles=["user"])
        token = self.create_token(auth_user)
        return auth_user, token

    def create_token(self, user: AuthenticatedUser, expires_in: int = 60 * 60 * 8) -> str:
        payload = {
            "sub": user.user_id,
            "username": user.username,
            "display_name": user.display_name,
            "roles": user.roles,
            "exp": int(time.time()) + expires_in,
            "jti": str(uuid.uuid4()),
        }
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

    def decode_token(self, token: str) -> dict:
        padded = token + "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("utf-8"))
        payload = json.loads(raw.decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("token expired")
        return payload

    def login(self, username: str, password: str) -> tuple[AuthenticatedUser, str]:
        user = self.db.execute(select(User).where(User.username == username, User.is_active.is_(True))).scalar_one_or_none()
        if user is None or not self.verify_password(password, user.password_hash):
            raise ValueError("invalid credentials")

        roles = self.list_roles(user.user_id)
        auth_user = AuthenticatedUser(
            user_id=user.user_id,
            username=user.username,
            display_name=user.display_name,
            email=user.email,
            roles=roles,
        )
        token = self.create_token(auth_user)
        return auth_user, token

    def list_roles(self, user_id: str) -> list[str]:
        stmt = select(Role.role_name).join(UserRole, UserRole.role_id == Role.role_id).where(UserRole.user_id == user_id)
        return list(self.db.execute(stmt).scalars().all())

    def get_current_user(self, token: str) -> AuthenticatedUser:
        payload = self.decode_token(token)
        user_id = payload.get("sub")
        user = self.db.get(User, user_id)
        if user is None:
            raise ValueError("user not found")
        return AuthenticatedUser(
            user_id=user.user_id,
            username=user.username,
            display_name=user.display_name,
            email=user.email,
            roles=list(payload.get("roles") or []),
        )
