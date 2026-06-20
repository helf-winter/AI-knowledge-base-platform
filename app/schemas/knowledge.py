from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentCreateResponse(BaseModel):
    document_id: str
    file_name: str
    parse_status: str


class ManualKnowledgeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=50000)
    knowledge_category: str = Field(default="manual", min_length=1, max_length=128)
    allowed_job_categories: str | None = Field(default=None, max_length=1000)
    business_purpose: str | None = Field(default=None, max_length=1000)
    tags: str | None = Field(default=None, max_length=500)


class DocumentItem(BaseModel):
    document_id: str
    owner_user_id: str | None = None
    effective_knowledge_space: str | None = None
    public_ref_id: str | None = None
    public_ref_status: str | None = None
    public_ref_category: str | None = None
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
    owner_user_id: str | None = None
    effective_knowledge_space: str | None = None
    public_ref_id: str | None = None
    public_ref_status: str | None = None
    public_ref_category: str | None = None
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
    knowledge_categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    knowledge_spaces: list[str] = Field(default_factory=list)
    file_types: list[str] = Field(default_factory=list)
    allowed_job_categories: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query: str
    results: list[ChunkItem]


class KnowledgeFilterOptions(BaseModel):
    knowledge_categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    knowledge_spaces: list[str] = Field(default_factory=list)
    file_types: list[str] = Field(default_factory=list)
    allowed_job_categories: list[str] = Field(default_factory=list)


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
    document_content_preview: str | None = None
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


class PublicKnowledgeRefRead(BaseModel):
    ref_id: str
    document_id: str
    document_name: str | None = None
    owner_user_id: str | None = None
    publish_request_id: str | None = None
    target_category: str
    allowed_job_categories: str
    status: str
    created_by: str | None = None
    disabled_by: str | None = None
    disabled_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class PublicKnowledgeSuggestionCreate(BaseModel):
    document_id: str = Field(min_length=1, max_length=36)
    suggestion_type: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=1, max_length=2000)
    suggestion: str = Field(min_length=1, max_length=5000)
    business_impact: str = Field(min_length=1, max_length=2000)


class PublicKnowledgeSuggestionRead(BaseModel):
    suggestion_id: str
    document_id: str
    document_name: str | None = None
    public_ref_id: str | None = None
    requester_id: str
    requester_name: str | None = None
    requester_employee_no: str | None = None
    suggestion_type: str
    question: str
    suggestion: str
    business_impact: str
    status: str
    reviewed_by: str | None = None
    review_comment: str | None = None
    reviewed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class PublicKnowledgeSuggestionReview(BaseModel):
    status: str = Field(pattern="^(accepted|rejected|need_more_info)$")
    review_comment: str = Field(min_length=1, max_length=1000)


class KnowledgeMergeScanRequest(BaseModel):
    min_score: float = Field(default=0.3, ge=0.0, le=1.0)


class KnowledgeMergeSuggestionRead(BaseModel):
    suggestion_id: str
    source_document_ids: list[str]
    source_document_names: list[str] = Field(default_factory=list)
    suggested_title: str
    suggested_category: str | None = None
    suggested_outline: str | None = None
    suggested_content: str
    similarity_reason: str
    generation_method: str = "rule_fallback"
    conflict_notes: str | None = None
    source_attributions: str | None = None
    status: str
    requester_id: str | None = None
    reviewed_by: str | None = None
    review_comment: str | None = None
    merged_document_id: str | None = None
    reviewed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class KnowledgeMergeReviewRequest(BaseModel):
    approve: bool
    review_comment: str | None = Field(default=None, max_length=1000)
    archive_sources: bool = False
