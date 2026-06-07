from __future__ import annotations

from pydantic import BaseModel


class TaskRead(BaseModel):
    task_id: str
    task_type: str
    related_document_id: str | None = None
    status: str
    retry_count: int
    error_message: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
