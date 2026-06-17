from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentCreateResponse(BaseModel):
    document_id: str
    file_name: str
    parse_status: str


class DocumentItem(BaseModel):
    document_id: str
    file_name: str
    file_type: str
    file_size: int
    parse_status: str
    visibility: str
    visibility_type: str = "private"
    knowledge_space: str = "personal"
    visibility_scope: str | None = None
    allowed_job_categories: str | None = None
    knowledge_category: str | None = None
    publish_status: str = "none"
    allowed_departments: str | None = None
    min_permission_level: int = 1
    security_level: str = "internal"
    is_public: bool = False
    document_status: str = "active"
    can_access: bool = True
    need_apply: bool = False
    access_reason: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ChunkItem(BaseModel):
    chunk_id: str
    document_id: str
    chunk_index: int
    content: str
    page_start: int | None = None
    page_end: int | None = None
    score: float | None = None
    source_file_name: str | None = None
    file_type: str | None = None
    updated_at: str | None = None
    can_access: bool = True
    need_apply: bool = False
    access_reason: str | None = None


class DocumentDetail(BaseModel):
    document_id: str
    file_name: str
    file_type: str
    file_size: int
    parse_status: str
    visibility: str
    visibility_type: str = "private"
    knowledge_space: str = "personal"
    visibility_scope: str | None = None
    allowed_job_categories: str | None = None
    knowledge_category: str | None = None
    publish_status: str = "none"
    allowed_departments: str | None = None
    min_permission_level: int = 1
    security_level: str = "internal"
    is_public: bool = False
    document_status: str = "active"
    can_access: bool = True
    need_apply: bool = False
    access_reason: str | None = None
    storage_path: str
    checksum: str
    content_text: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    chunks: list[ChunkItem] = Field(default_factory=list)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    user_id: str
    session_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResponse(BaseModel):
    query: str
    results: list[ChunkItem]


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    user_id: str
    session_id: str | None = None
    agent_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    knowledge_reference: list[ChunkItem]
    confidence: float = 0.0
    trace_id: str
    recommended_agent_id: str | None = None
    recommended_agent_name: str | None = None
    recommended_reason: str | None = None


class KnowledgeExpansionRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    answer: str = Field(min_length=1, max_length=10000)
    trace_id: str | None = None
    target_document_id: str | None = None


class KnowledgeExpansionResponse(BaseModel):
    document_id: str
    knowledge_id: str | None = None
    action: str
    title: str


class FeedbackCreate(BaseModel):
    session_id: str
    answer_id: str
    rating: int = Field(ge=1, le=5)
    is_helpful: bool
    comment: str | None = None
    issue_type: str | None = None


class AccessCheckResponse(BaseModel):
    document_id: str
    can_access: bool
    reason: str
    need_apply: bool


class AccessRequestCreate(BaseModel):
    document_id: str = Field(min_length=1, max_length=36)
    reason: str = Field(min_length=1, max_length=1000)
    business_purpose: str = Field(min_length=1, max_length=1000)
    expected_duration: str | None = Field(default=None, max_length=64)


class AccessRequestRead(BaseModel):
    request_id: str
    user_id: str
    document_id: str
    applicant_name: str | None = None
    applicant_employee_no: str | None = None
    applicant_department: str | None = None
    applicant_permission_level: int | None = None
    document_name: str | None = None
    document_security_level: str | None = None
    document_min_permission_level: int | None = None
    reason: str
    business_purpose: str
    expected_duration: str | None = None
    status: str
    ai_suggestion: str | None = None
    ai_risk_level: str | None = None
    ai_reason: str | None = None
    reviewed_by: str | None = None
    review_comment: str | None = None
    reviewed_at: str | None = None
    created_at: str | None = None


class AccessReviewRequest(BaseModel):
    approve: bool
    review_comment: str | None = Field(default=None, max_length=1000)


class AIAccessReviewResponse(BaseModel):
    request_id: str
    suggestion: str
    risk_level: str
    reason: str


class KnowledgePublishRequestCreate(BaseModel):
    document_id: str = Field(min_length=1, max_length=36)
    target_category: str = Field(min_length=1, max_length=128)
    allowed_job_categories: str = Field(min_length=1, max_length=1000)
    publish_reason: str = Field(min_length=1, max_length=1000)
    business_purpose: str = Field(min_length=1, max_length=1000)


class KnowledgePublishRequestRead(BaseModel):
    request_id: str
    document_id: str
    requester_id: str
    requester_name: str | None = None
    requester_employee_no: str | None = None
    document_name: str | None = None
    target_category: str
    allowed_job_categories: str
    publish_reason: str
    business_purpose: str
    status: str
    reviewed_by: str | None = None
    review_comment: str | None = None
    reviewed_at: str | None = None
    created_at: str | None = None


class KnowledgePublishReviewRequest(BaseModel):
    approve: bool
    review_comment: str | None = Field(default=None, max_length=1000)
