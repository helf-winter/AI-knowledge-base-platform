from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.core import Department, Role, User, UserRole


@dataclass
class AuthenticatedUser:
    user_id: str
    username: str
    employee_no: str | None
    display_name: str
    email: str | None
    department: str | None
    position: str | None
    permission_level: int
    is_first_login: bool
    status: str
    roles: list[str]


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _hash_password(self, password: str) -> str:
        salt = os.urandom(16).hex()
        iterations = 120_000
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations).hex()
        return f"pbkdf2_sha256${iterations}${salt}${digest}"

    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        if password_hash.startswith("pbkdf2_sha256$"):
            _, iterations, salt, digest = password_hash.split("$", 3)
            candidate = hashlib.pbkdf2_hmac(
                "sha256",
                plain_password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations),
            ).hex()
            return hmac.compare_digest(candidate, digest)

        # Backward compatibility for early demo accounts created with sha256.
        legacy = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(legacy, password_hash)

    def seed_default_admin(self) -> None:
        admin_department = self._get_or_create_department("平台管理部")
        it_department = self._get_or_create_department("信息技术部")
        admin_role = self._get_or_create_role("admin")
        user_role = self._get_or_create_role("user")

        admin = self.db.execute(select(User).where(User.username == "admin")).scalar_one_or_none()
        if admin is None:
            admin = User(
                user_id=str(uuid.uuid4()),
                department_id=admin_department.department_id,
                username="admin",
                employee_no="E0001",
                display_name="系统管理员",
                email="admin@example.com",
                position="平台管理员",
                permission_level=9,
                initial_password_code="123456",
                is_first_login=True,
                status="active",
                password_hash=self._hash_password("123456"),
                is_active=True,
            )
            self.db.add(admin)
            self.db.flush()
        else:
            admin.department_id = admin.department_id or admin_department.department_id
            admin.employee_no = admin.employee_no or "E0001"
            admin.position = admin.position or "平台管理员"
            admin.permission_level = max(int(admin.permission_level or 1), 9)
            admin.initial_password_code = admin.initial_password_code or "123456"
            admin.status = admin.status or ("active" if admin.is_active else "disabled")

        self._assign_role(admin.user_id, admin_role.role_id)

        demo_user = self.db.execute(select(User).where(or_(User.username == "zhangsan", User.employee_no == "E1001"))).scalar_one_or_none()
        if demo_user is None:
            demo_user = User(
                user_id=str(uuid.uuid4()),
                department_id=it_department.department_id,
                username="zhangsan",
                employee_no="E1001",
                display_name="张三",
                email="zhangsan@example.com",
                position="研发工程师",
                permission_level=3,
                initial_password_code="654321",
                is_first_login=True,
                status="active",
                password_hash=self._hash_password("654321"),
                is_active=True,
            )
            self.db.add(demo_user)
            self.db.flush()

        self._assign_role(demo_user.user_id, user_role.role_id)
        self.db.commit()

    def register(self, username: str, password: str, display_name: str, email: str | None = None) -> tuple[AuthenticatedUser, str]:
        raise ValueError("self registration is disabled")

    def login(self, employee_no: str, password: str) -> tuple[AuthenticatedUser, str]:
        user = self.db.execute(select(User).where(or_(User.employee_no == employee_no, User.username == employee_no))).scalar_one_or_none()
        if user is not None and (not user.is_active or user.status == "disabled"):
            raise ValueError("user disabled")
        if user is None or not self.verify_password(password, user.password_hash):
            raise ValueError("invalid credentials")

        auth_user = self._to_authenticated_user(user)
        token = self.create_token(auth_user)
        return auth_user, token

    def change_initial_password(self, user_id: str, old_password: str, new_password: str) -> tuple[AuthenticatedUser, str]:
        user = self.db.get(User, user_id)
        if user is None:
            raise ValueError("user not found")
        if not user.is_first_login:
            raise ValueError("initial password already changed")
        if not self.verify_password(old_password, user.password_hash):
            raise ValueError("old password is incorrect")
        if old_password == new_password:
            raise ValueError("new password must be different from initial password")

        user.password_hash = self._hash_password(new_password)
        user.is_first_login = False
        self.db.commit()
        self.db.refresh(user)

        auth_user = self._to_authenticated_user(user)
        token = self.create_token(auth_user)
        return auth_user, token

    def verify_user_password(self, user_id: str, password: str) -> bool:
        user = self.db.get(User, user_id)
        if user is None:
            raise ValueError("user not found")
        return self.verify_password(password, user.password_hash)

    def create_token(self, user: AuthenticatedUser, expires_in: int = 60 * 60 * 8) -> str:
        payload = {
            "sub": user.user_id,
            "username": user.username,
            "employee_no": user.employee_no,
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

    def list_roles(self, user_id: str) -> list[str]:
        stmt = select(Role.role_name).join(UserRole, UserRole.role_id == Role.role_id).where(UserRole.user_id == user_id)
        return list(self.db.execute(stmt).scalars().all())

    def get_current_user(self, token: str) -> AuthenticatedUser:
        payload = self.decode_token(token)
        user = self.db.get(User, payload.get("sub"))
        if user is None:
            raise ValueError("user not found")
        if not user.is_active or user.status == "disabled":
            raise ValueError("user disabled")
        return self._to_authenticated_user(user)

    def get_user_by_id(self, user_id: str) -> AuthenticatedUser | None:
        user = self.db.get(User, user_id)
        if user is None or not user.is_active or user.status == "disabled":
            return None
        return self._to_authenticated_user(user)

    def _get_or_create_department(self, name: str) -> Department:
        department = self.db.execute(select(Department).where(Department.department_name == name)).scalar_one_or_none()
        if department is None:
            department = Department(department_id=str(uuid.uuid4()), department_name=name)
            self.db.add(department)
            self.db.flush()
        return department

    def _get_or_create_role(self, name: str) -> Role:
        role = self.db.execute(select(Role).where(Role.role_name == name)).scalar_one_or_none()
        if role is None:
            role = Role(role_id=str(uuid.uuid4()), role_name=name)
            self.db.add(role)
            self.db.flush()
        return role

    def _assign_role(self, user_id: str, role_id: str) -> None:
        existed = self.db.execute(select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)).scalar_one_or_none()
        if existed is None:
            self.db.add(UserRole(user_id=user_id, role_id=role_id))

    def _to_authenticated_user(self, user: User) -> AuthenticatedUser:
        department = self.db.get(Department, user.department_id) if user.department_id else None
        return AuthenticatedUser(
            user_id=user.user_id,
            username=user.username,
            employee_no=user.employee_no,
            display_name=user.display_name,
            email=user.email,
            department=department.department_name if department else None,
            position=user.position,
            permission_level=int(user.permission_level or 1),
            is_first_login=bool(user.is_first_login),
            status=user.status or ("active" if user.is_active else "disabled"),
            roles=self.list_roles(user.user_id),
        )
