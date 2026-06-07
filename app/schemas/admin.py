from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class KnowledgeMetadataCreate(BaseModel):
    document_id: str
    title: str = Field(min_length=1, max_length=255)
    author: str | None = None
    knowledge_type: str = Field(min_length=1, max_length=64)
    version: str = Field(default="v1.0.0", max_length=32)
    status: str = Field(default="reviewing", max_length=32)
    source_type: str = Field(default="upload", max_length=32)
    acl_json: str | None = None


class KnowledgeMetadataUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    author: str | None = None
    knowledge_type: str | None = Field(default=None, max_length=64)
    version: str | None = Field(default=None, max_length=32)
    status: str | None = Field(default=None, max_length=32)
    source_type: str | None = Field(default=None, max_length=32)
    acl_json: str | None = None


class KnowledgeMetadataRead(BaseModel):
    knowledge_id: str
    document_id: str
    title: str
    author: str | None
    knowledge_type: str
    version: str
    status: str
    source_type: str
    acl_json: str | None
    is_archived: bool = False
    deleted_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ExpertAgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    knowledge_domain: str = Field(min_length=1, max_length=128)
    knowledge_scope_json: str | None = None
    skills_json: str | None = None
    model_name: str = Field(default="deepseek", max_length=64)
    prompt_version: str = Field(default="v1", max_length=32)
    status: str = Field(default="active", max_length=32)


class ExpertAgentRead(BaseModel):
    agent_id: str
    name: str
    description: str | None
    knowledge_domain: str
    knowledge_scope_json: str | None
    skills_json: str | None = None
    model_name: str
    prompt_version: str
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class KnowledgeHotnessRead(BaseModel):
    document_id: str
    title: str
    search_count: int
    answer_count: int
    total_hotness: int


class KnowledgeArchiveActionRead(BaseModel):
    knowledge_id: str
    is_archived: bool
    deleted_at: datetime | None = None


class ExpertAgentListResponse(BaseModel):
    items: list[ExpertAgentRead]


class SkillDescriptor(BaseModel):
    skill_id: str
    name: str
    version: str
    description: str
    capabilities: list[str] = Field(default_factory=list)


class SkillCatalogRead(BaseModel):
    items: list[SkillDescriptor]
