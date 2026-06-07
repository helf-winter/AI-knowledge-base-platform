from __future__ import annotations

from pydantic import BaseModel, Field


class KnowledgeGapCreate(BaseModel):
    query_text: str = Field(min_length=1)
    session_id: str | None = None
    user_id: str | None = None
    answer_id: str | None = None
    issue_type: str = Field(default="missing_knowledge")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: str | None = None


class KnowledgeGapReview(BaseModel):
    approved: bool
    title: str | None = None
    content: str | None = None


class KnowledgeGapRecord(BaseModel):
    gap_id: str
    query_text: str
    session_id: str | None = None
    user_id: str | None = None
    answer_id: str | None = None
    issue_type: str
    confidence: float
    evidence: str | None = None
    suggested_title: str | None = None
    suggested_content: str | None = None
    status: str
    created_at: str | None = None


class LearningInsightRead(BaseModel):
    topic: str
    count: int
    sample_questions: list[str]
    suggested_title: str
    suggested_content: str


class LearningAnalysisRead(BaseModel):
    insights: list[LearningInsightRead]
    total_gaps: int
    status: str
