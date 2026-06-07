from __future__ import annotations

from pydantic import BaseModel, Field


class SkillMeta(BaseModel):
    skill_id: str
    name: str
    description: str
    version: str = "1.0.0"
    tags: list[str] = Field(default_factory=list)
    timeout_ms: int = 3000
    enabled: bool = True


class SkillRequest(BaseModel):
    trace_id: str
    user_id: str | None = None
    session_id: str | None = None
    input: dict


class SkillResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    trace_id: str | None = None
    data: dict | None = None
