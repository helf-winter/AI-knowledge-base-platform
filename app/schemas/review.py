from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    review_type: str = Field(pattern="^(answer_quality|document_access|knowledge_publish|learning_gap_draft)$")
    subject: dict[str, Any]
    context: dict[str, Any] = Field(default_factory=dict)


class ReviewResult(BaseModel):
    review_type: str
    suggestion: str = Field(pattern="^(approve|reject|review)$")
    risk_level: str = Field(pattern="^(low|medium|high)$")
    reason: str
    missing_information: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    next_action: str | None = None
