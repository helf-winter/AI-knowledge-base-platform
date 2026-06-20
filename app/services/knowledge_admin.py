from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundAppError, ValidationAppError
from app.models.core import Answer, AuditLog, ExpertAgentProfile, KnowledgeMetadata
from app.models.document import Document
from app.schemas.admin import (
    ExpertAgentCreate,
    KnowledgeHotnessRead,
    KnowledgeMetadataCreate,
    KnowledgeMetadataUpdate,
    SkillDescriptor,
)


class KnowledgeAdminService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _get_metadata(self, knowledge_id: str) -> KnowledgeMetadata:
        item = self.db.get(KnowledgeMetadata, knowledge_id)
        if item is None:
            raise NotFoundAppError("知识元数据不存在")
        return item

    def create_metadata(self, payload: KnowledgeMetadataCreate) -> KnowledgeMetadata:
        existed = self.db.execute(select(KnowledgeMetadata).where(KnowledgeMetadata.document_id == payload.document_id)).scalar_one_or_none()
        if existed:
            raise ValidationAppError("该文档已存在知识元数据，请执行更新而不是重复创建")
        item = KnowledgeMetadata(
            knowledge_id=str(uuid.uuid4()),
            document_id=payload.document_id,
            title=payload.title,
            author=payload.author,
            knowledge_type=payload.knowledge_type,
            version=payload.version,
            status=payload.status,
            source_type=payload.source_type,
            acl_json=payload.acl_json,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update_metadata(self, knowledge_id: str, payload: KnowledgeMetadataUpdate) -> KnowledgeMetadata:
        item = self._get_metadata(knowledge_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        self.db.commit()
        self.db.refresh(item)
        return item

    def archive_metadata(self, knowledge_id: str) -> KnowledgeMetadata:
        item = self._get_metadata(knowledge_id)
        item.is_archived = True
        item.deleted_at = datetime.now(timezone.utc)
        item.status = "disabled"
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete_metadata(self, knowledge_id: str) -> KnowledgeMetadata:
        item = self._get_metadata(knowledge_id)
        self.db.delete(item)
        self.db.commit()
        return item

    def list_metadata(self, status: str | None = None, document_id: str | None = None, include_archived: bool = False) -> list[KnowledgeMetadata]:
        stmt = select(KnowledgeMetadata)
        if status:
            stmt = stmt.where(KnowledgeMetadata.status == status)
        if document_id:
            stmt = stmt.where(KnowledgeMetadata.document_id == document_id)
        if not include_archived:
            stmt = stmt.where(KnowledgeMetadata.is_archived.is_(False))
        return list(self.db.execute(stmt.order_by(KnowledgeMetadata.created_at.desc())).scalars().all())

    def review_metadata(self, knowledge_id: str, approve: bool) -> KnowledgeMetadata:
        item = self._get_metadata(knowledge_id)
        item.status = "available" if approve else "disabled"
        self.db.commit()
        self.db.refresh(item)
        return item

    def create_expert_agent(self, payload: ExpertAgentCreate) -> ExpertAgentProfile:
        existed = self.db.execute(select(ExpertAgentProfile).where(ExpertAgentProfile.agent_name == payload.name)).scalar_one_or_none()
        if existed:
            raise ValidationAppError("该专家 Agent 名称已存在")
        values = dict(
            agent_id=str(uuid.uuid4()),
            agent_name=payload.name,
            domain_name=payload.knowledge_domain,
            description=payload.description,
            knowledge_scope_json=payload.knowledge_scope_json,
            status=payload.status,
        )
        if self._expert_agent_supports_skills_json():
            values["skills_json"] = payload.skills_json
        item = ExpertAgentProfile(**values)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_expert_agents(self) -> list[ExpertAgentProfile]:
        if self._expert_agent_supports_skills_json():
            stmt = select(ExpertAgentProfile).order_by(ExpertAgentProfile.created_at.desc())
            return list(self.db.execute(stmt).scalars().all())
        stmt = text("""
            SELECT agent_id, agent_name, domain_name, description, knowledge_scope_json, status, created_at, updated_at
            FROM expert_agent_profiles
            ORDER BY created_at DESC
        """)
        rows = list(self.db.execute(stmt).mappings().all())
        items: list[ExpertAgentProfile] = []
        for row in rows:
            item = ExpertAgentProfile(
                agent_id=row["agent_id"],
                agent_name=row["agent_name"],
                domain_name=row["domain_name"],
                description=row["description"],
                knowledge_scope_json=row["knowledge_scope_json"],
                status=row["status"],
            )
            setattr(item, "created_at", row["created_at"])
            setattr(item, "updated_at", row["updated_at"])
            setattr(item, "skills_json", None)
            items.append(item)
        return items

    def _expert_agent_supports_skills_json(self) -> bool:
        try:
            inspector = inspect(self.db.bind)
            columns = [col.get("name") for col in inspector.get_columns("expert_agent_profiles")]
            return "skills_json" in columns
        except Exception:
            return False

    def get_agent_skill_descriptors(self, skills_json: str | None) -> list[SkillDescriptor]:
        if not skills_json:
            return []
        try:
            selected = json.loads(skills_json)
        except Exception:
            return []
        items = {skill.skill_id: skill for skill in self.catalog_skills()}
        result: list[SkillDescriptor] = []
        for skill_id in selected:
            skill = items.get(skill_id)
            if skill is not None:
                result.append(skill)
        return result

    def hotness_stats(self, limit: int = 20) -> list[KnowledgeHotnessRead]:
        docs = self.db.execute(select(Document.document_id, Document.file_name).order_by(Document.created_at.desc()).limit(limit)).all()
        items: list[KnowledgeHotnessRead] = []
        for doc_id, file_name in docs:
            search_count = self.db.execute(
                select(func.count(AuditLog.log_id)).where(
                    AuditLog.action.in_(["search_knowledge", "chat_stream"]),
                    AuditLog.payload_json.contains(doc_id),
                )
            ).scalar_one() or 0
            answer_count = self.db.execute(select(func.count(Answer.answer_id)).where(Answer.query_text.contains(file_name))).scalar_one() or 0
            items.append(
                KnowledgeHotnessRead(
                    document_id=doc_id,
                    title=file_name,
                    search_count=int(search_count),
                    answer_count=int(answer_count),
                    total_hotness=int(search_count) + int(answer_count),
                )
            )
        return items

    def catalog_skills(self) -> list[SkillDescriptor]:
        return [
            SkillDescriptor(
                skill_id="knowledge_search",
                name="查找制度依据",
                version="v1",
                description="从用户可访问的知识库中检索依据、来源和可引用片段，用于制度问答和专家回答。",
                capabilities=["知识检索", "依据引用", "问答上下文"],
            ),
            SkillDescriptor(
                skill_id="document_summarize",
                name="总结文档",
                version="v1",
                description="把长文档整理成摘要、要点和适用场景，帮助用户快速理解知识内容。",
                capabilities=["文档摘要", "关键要点", "阅读辅助"],
            ),
            SkillDescriptor(
                skill_id="knowledge_extract",
                name="提取流程步骤",
                version="v1",
                description="从文档或回答中提取流程、条件、注意事项和结构化知识。",
                capabilities=["流程提取", "知识结构化", "生成培训题"],
            ),
            SkillDescriptor(
                skill_id="knowledge_compare",
                name="对比知识差异",
                version="v1",
                description="对比不同知识片段、版本或草稿之间的差异，辅助审核与更新。",
                capabilities=["差异对比", "版本核查", "冲突发现"],
            ),
            SkillDescriptor(
                skill_id="knowledge_gap_detect",
                name="发现知识缺口",
                version="v1",
                description="根据低置信度回答、用户反馈和通用兜底回答发现需要补充的知识。",
                capabilities=["缺口识别", "自动学习", "待补充问题"],
            ),
            SkillDescriptor(
                skill_id="publish_draft_generate",
                name="生成发布草稿",
                version="v1",
                description="把个人知识或问答补充内容整理为可提交审核的公有知识草稿。",
                capabilities=["草稿生成", "发布审核", "知识治理"],
            ),
        ]
