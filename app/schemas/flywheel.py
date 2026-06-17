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


class LearningGapDraftCreate(BaseModel):
    target_category: str = Field(min_length=1, max_length=128)
    allowed_job_categories: str = Field(min_length=1, max_length=1000)
    business_purpose: str = Field(min_length=1, max_length=1000)


class LearningGapDraftReview(BaseModel):
    approve: bool
    admin_final_content: str | None = Field(default=None, max_length=20000)
    target_category: str | None = Field(default=None, max_length=128)
    allowed_job_categories: str | None = Field(default=None, max_length=1000)
    review_comment: str | None = Field(default=None, max_length=1000)


class KnowledgeGapRecord(BaseModel):
    gap_id: str
    query_text: str
    session_id: str | None = None
    user_id: str | None = None
    answer_id: str | None = None
    issue_type: str
    confidence: float
    evidence: str | None = None
    normalized_question: str | None = None
    cluster_key: str | None = None
    hit_count: int = 1
    suggested_title: str | None = None
    suggested_content: str | None = None
    draft_document_id: str | None = None
    ai_draft_content: str | None = None
    pending_confirmations: str | None = None
    admin_final_content: str | None = None
    target_category: str | None = None
    allowed_job_categories: str | None = None
    business_purpose: str | None = None
    review_comment: str | None = None
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    status: str
    created_at: str | None = None
    updated_at: str | None = None


class LearningGapDraftRead(BaseModel):
    gap_id: str
    draft_document_id: str | None = None
    suggested_title: str | None = None
    ai_draft_content: str
    pending_confirmations: str
    status: str


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
