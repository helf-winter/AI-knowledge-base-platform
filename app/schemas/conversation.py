from __future__ import annotations

from pydantic import BaseModel, Field


class ConversationTurnCreate(BaseModel):
    session_id: str
    user_id: str | None = None
    query_text: str = Field(min_length=1)
    answer_text: str = Field(min_length=1)
    confidence: float = 0.0
    source_refs_json: str = Field(default="[]")
    model_name: str = Field(default="deepseek", max_length=64)
    prompt_version: str = Field(default="v1", max_length=32)
    trace_id: str | None = None


class ConversationTurnRead(BaseModel):
    turn_id: str
    session_id: str
    user_id: str | None = None
    query_text: str
    answer_text: str
    confidence: float
    source_refs_json: str
    model_name: str
    prompt_version: str
    trace_id: str | None = None
