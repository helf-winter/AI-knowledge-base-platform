from __future__ import annotations

import json
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import AuditLog, User


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(self, *, user_id: str | None, action: str, resource_type: str, resource_id: str | None = None, trace_id: str, payload: dict | None = None) -> AuditLog:
        safe_user_id = user_id if self._user_exists(user_id) else None
        item = AuditLog(
            log_id=str(uuid.uuid4()),
            user_id=safe_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            trace_id=trace_id,
            payload_json=json.dumps(payload, ensure_ascii=False) if payload is not None else None,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def _user_exists(self, user_id: str | None) -> bool:
        if not user_id:
            return False
        return self.db.execute(select(User.user_id).where(User.user_id == user_id)).scalar_one_or_none() is not None
