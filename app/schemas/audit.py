from __future__ import annotations

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    log_id: str
    user_id: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    trace_id: str
    payload_json: str | None = None
    created_at: str | None = None
