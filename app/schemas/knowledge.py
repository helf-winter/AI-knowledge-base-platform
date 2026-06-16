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


class DocumentDetail(BaseModel):
    document_id: str
    file_name: str
    file_type: str
    file_size: int
    parse_status: str
    visibility: str
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
