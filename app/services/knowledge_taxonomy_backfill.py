from __future__ import annotations

from datetime import datetime, timezone
import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import DocumentTag, Tag
from app.models.document import Document
from app.services.deepseek import DeepSeekClient


KNOWLEDGE_CATEGORIES = [
    "IT与技术",
    "研发知识",
    "制度规范",
    "人力资源",
    "财务报销",
    "业务流程",
    "数据处理",
    "设计知识",
    "培训资料",
    "整合知识",
    "其他",
]


class KnowledgeTaxonomyBackfillService:
    def __init__(self, db: Session, deepseek_client: DeepSeekClient | None = None) -> None:
        self.db = db
        self.deepseek = deepseek_client or DeepSeekClient()

    def build_plan(self, limit: int | None = None, batch_size: int = 5) -> dict[str, object]:
        stmt = select(Document).order_by(Document.created_at.asc())
        if limit:
            stmt = stmt.limit(limit)
        documents = list(self.db.execute(stmt).scalars().all())
        existing_tags = self._existing_tags([document.document_id for document in documents])
        candidates = [
            document
            for document in documents
            if not (document.knowledge_category or "").strip() or not existing_tags.get(document.document_id)
        ]

        suggestions: dict[str, tuple[dict[str, object], str]] = {}
        for start in range(0, len(candidates), max(1, batch_size)):
            batch = candidates[start : start + max(1, batch_size)]
            ai_items = self._ask_deepseek(batch)
            for document in batch:
                ai_suggestion = ai_items.get(document.document_id)
                if ai_suggestion:
                    suggestions[document.document_id] = (ai_suggestion, "deepseek")
                else:
                    suggestions[document.document_id] = (self._fallback_suggestion(document), "rule_fallback")

        items = []
        for document in candidates:
            suggestion, method = suggestions[document.document_id]
            items.append(
                self._make_plan_item(
                    document,
                    existing_tags=existing_tags.get(document.document_id, []),
                    suggestion=suggestion,
                    method=method,
                )
            )
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "allowed_categories": KNOWLEDGE_CATEGORIES,
            "document_count": len(documents),
            "candidate_count": len(candidates),
            "items": items,
        }

    def apply_plan(self, plan: dict[str, object]) -> dict[str, int]:
        raw_items = plan.get("items")
        if not isinstance(raw_items, list):
            raise ValueError("补全计划缺少 items")

        category_updates = 0
        tag_updates = 0
        skipped = 0
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                skipped += 1
                continue
            document_id = str(raw_item.get("document_id") or "").strip()
            document = self.db.get(Document, document_id)
            if document is None:
                skipped += 1
                continue

            category = self._normalize_category(raw_item.get("category"))
            if not (document.knowledge_category or "").strip() and category:
                document.knowledge_category = category
                category_updates += 1

            current_tags = self._existing_tags([document.document_id]).get(document.document_id, [])
            if not current_tags:
                tag_names = self._normalize_tags(raw_item.get("tags"))
                for tag_name in tag_names:
                    tag = self.db.execute(select(Tag).where(Tag.tag_name == tag_name)).scalar_one_or_none()
                    if tag is None:
                        tag = Tag(tag_id=str(uuid.uuid4()), tag_name=tag_name, tag_type="business")
                        self.db.add(tag)
                        self.db.flush()
                    self.db.add(DocumentTag(document_id=document.document_id, tag_id=tag.tag_id))
                    tag_updates += 1

        self.db.commit()
        return {
            "category_updates": category_updates,
            "tag_links_created": tag_updates,
            "skipped": skipped,
        }

    def _ask_deepseek(self, documents: list[Document]) -> dict[str, dict[str, object]]:
        if not documents:
            return {}
        payload = {
            "task": "为历史企业知识文档补充知识类别和检索标签。只能根据标题和正文摘要判断，不得编造文档内容。",
            "allowed_categories": KNOWLEDGE_CATEGORIES,
            "requirements": [
                "每个文档必须从 allowed_categories 中选择一个 category",
                "每个文档生成 3 到 6 个简短中文标签",
                "标签应包含主题、业务场景或技术关键词，避免使用无意义的通用词",
            ],
            "output_schema": {
                "items": [{"document_id": "文档ID", "category": "类别", "tags": ["标签"]}],
            },
            "documents": [
                {
                    "document_id": document.document_id,
                    "file_name": document.file_name,
                    "file_type": document.file_type,
                    "existing_category": document.knowledge_category,
                    "content_excerpt": (document.content_text or "")[:1600],
                }
                for document in documents
            ],
        }
        result = self.deepseek.complete_json(
            "你是企业知识分类助手。只输出 JSON，不修改原文，不输出 Markdown。",
            payload,
            temperature=0.1,
            timeout=90.0,
        )
        raw_items = result.get("items") if isinstance(result, dict) else None
        if not isinstance(raw_items, list):
            return {}
        suggestions: dict[str, dict[str, object]] = {}
        valid_ids = {document.document_id for document in documents}
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            document_id = str(item.get("document_id") or "")
            if document_id in valid_ids:
                suggestions[document_id] = item
        return suggestions

    def _make_plan_item(
        self,
        document: Document,
        existing_tags: list[str],
        suggestion: dict[str, object],
        method: str,
    ) -> dict[str, object]:
        existing_category = (document.knowledge_category or "").strip()
        category = existing_category or self._normalize_category(suggestion.get("category")) or "其他"
        normalized_existing_tags = self._normalize_tags(existing_tags)
        tags = normalized_existing_tags or self._normalize_tags(suggestion.get("tags"))
        if not tags:
            tags = self._fallback_suggestion(document)["tags"]
        return {
            "document_id": document.document_id,
            "file_name": document.file_name,
            "category": category,
            "tags": tags,
            "category_changed": not bool(existing_category),
            "tags_changed": not bool(normalized_existing_tags),
            "method": method,
        }

    def _fallback_suggestion(self, document: Document) -> dict[str, object]:
        text = f"{document.file_name} {document.content_text or ''}".lower()
        tags: list[str] = []
        if "vpn" in text:
            category = "IT与技术"
            tags.append("VPN")
            if any(keyword in text for keyword in ("申请", "权限", "账号")):
                tags.append("权限申请")
            if any(keyword in text for keyword in ("远程", "内网", "连接")):
                tags.append("远程办公")
        elif any(keyword in text for keyword in ("vue", "react", "前端", "javascript", "css", "浏览器")):
            category = "研发知识"
            tags.append("前端")
            if "vue" in text:
                tags.append("Vue")
            if "性能" in text:
                tags.append("性能优化")
            if "面试" in text:
                tags.append("面试题")
        elif any(keyword in text for keyword in ("报销", "发票", "财务")):
            category = "财务报销"
            tags.extend(["财务", "报销流程"])
        elif any(keyword in text for keyword in ("入职", "招聘", "员工", "人事")):
            category = "人力资源"
            tags.extend(["员工管理", "人力资源"])
        elif any(keyword in text for keyword in ("制度", "规范", "合规")):
            category = "制度规范"
            tags.extend(["制度", "规范"])
        elif document.file_type.lower() in {"csv", "xls", "xlsx"}:
            category = "数据处理"
            tags.extend(["表格", "数据处理"])
        else:
            category = "其他"
            tags.extend([document.file_type.upper() or "文档", "知识文档"])
        return {"category": category, "tags": self._normalize_tags(tags)}

    def _existing_tags(self, document_ids: list[str]) -> dict[str, list[str]]:
        if not document_ids:
            return {}
        rows = self.db.execute(
            select(DocumentTag.document_id, Tag.tag_name)
            .join(Tag, Tag.tag_id == DocumentTag.tag_id)
            .where(DocumentTag.document_id.in_(document_ids))
            .order_by(Tag.tag_name)
        ).all()
        result: dict[str, list[str]] = {}
        for document_id, tag_name in rows:
            result.setdefault(str(document_id), []).append(str(tag_name))
        return result

    def _normalize_category(self, value: object) -> str | None:
        category = str(value or "").strip()
        return category if category in KNOWLEDGE_CATEGORIES else None

    def _normalize_tags(self, value: object) -> list[str]:
        if isinstance(value, str):
            raw_values = re.split(r"[,，;；]", value)
        elif isinstance(value, (list, tuple, set)):
            raw_values = list(value)
        else:
            raw_values = []
        tags: list[str] = []
        seen: set[str] = set()
        for raw in raw_values:
            tag = str(raw or "").strip()[:64]
            if not tag or tag in seen:
                continue
            seen.add(tag)
            tags.append(tag)
            if len(tags) >= 6:
                break
        return tags
