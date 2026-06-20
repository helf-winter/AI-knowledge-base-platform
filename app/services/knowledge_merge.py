from __future__ import annotations

from datetime import datetime, timezone
import json
import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import NotFoundAppError, PermissionAppError, ValidationAppError
from app.models.core import KnowledgeMetadata
from app.models.document import Document, DocumentChunk, KnowledgeMergeSuggestion
from app.models.vector import ChunkEmbedding
from app.schemas.knowledge import ManualKnowledgeCreate
from app.services.access_control import DocumentAccessService
from app.services.auth import AuthenticatedUser
from app.services.deepseek import DeepSeekClient


class KnowledgeMergeService:
    def __init__(self, db: Session, deepseek_client: DeepSeekClient | None = None) -> None:
        self.db = db
        self.access = DocumentAccessService(db)
        self.deepseek = deepseek_client or DeepSeekClient()
        self.settings = get_settings()

    def scan(self, user: AuthenticatedUser, min_score: float = 0.3) -> list[KnowledgeMergeSuggestion]:
        documents = self._visible_documents(user)
        documents_by_id = {document.document_id: document for document in documents}
        vector_pairs = self._vector_candidate_pairs(documents)
        if not vector_pairs:
            vector_pairs = self._fallback_candidate_pairs(documents)

        created: list[KnowledgeMergeSuggestion] = []
        for (left_id, right_id), semantic_score in sorted(vector_pairs.items(), key=lambda item: item[1], reverse=True):
            if len(created) >= self.settings.knowledge_merge_max_suggestions:
                break
            left = documents_by_id.get(left_id)
            right = documents_by_id.get(right_id)
            if left is None or right is None:
                continue
            score, reason = self._combined_similarity(left, right, semantic_score)
            if score < min_score:
                continue
            source_ids = sorted([left.document_id, right.document_id])
            existed = self._find_existing(source_ids)
            if existed is not None:
                created.append(existed)
                continue

            draft = self._build_merge_draft(left, right, score)
            item = KnowledgeMergeSuggestion(
                suggestion_id=str(uuid.uuid4()),
                source_document_ids=json.dumps(source_ids, ensure_ascii=False),
                suggested_title=str(draft["suggested_title"]),
                suggested_category=str(draft["suggested_category"]),
                suggested_outline=str(draft["suggested_outline"]),
                suggested_content=str(draft["suggested_content"]),
                similarity_reason=reason,
                generation_method=str(draft["generation_method"]),
                conflict_notes=str(draft["conflict_notes"]),
                source_attributions=str(draft["source_attributions"]),
                status="pending",
                requester_id=user.user_id,
            )
            self.db.add(item)
            created.append(item)
        self.db.commit()
        for item in created:
            self.db.refresh(item)
        return created

    def list_suggestions(self, user: AuthenticatedUser, status: str | None = None, admin_view: bool = False) -> list[KnowledgeMergeSuggestion]:
        stmt = select(KnowledgeMergeSuggestion).order_by(KnowledgeMergeSuggestion.created_at.desc())
        if status:
            stmt = stmt.where(KnowledgeMergeSuggestion.status == status)
        items = list(self.db.execute(stmt).scalars().all())
        if admin_view:
            if not {"admin", "reviewer"}.intersection(set(user.roles)):
                raise PermissionAppError("只有管理员或审核员可以查看知识整合审核列表")
            return [item for item in items if self._admin_can_view(item, user)]
        return [item for item in items if item.requester_id == user.user_id or self._can_review(item, user, allow_admin=False)]

    def review(
        self,
        suggestion_id: str,
        approve: bool,
        reviewer: AuthenticatedUser,
        review_comment: str | None = None,
        archive_sources: bool = False,
    ) -> KnowledgeMergeSuggestion:
        item = self.db.get(KnowledgeMergeSuggestion, suggestion_id)
        if item is None:
            raise NotFoundAppError("知识整合建议不存在")
        if item.status != "pending":
            raise ValidationAppError("已处理的知识整合建议不能重复审核")
        if not self._can_review(item, reviewer, allow_admin=True):
            raise PermissionAppError("无权处理该知识整合建议")

        item.status = "approved" if approve else "rejected"
        item.reviewed_by = reviewer.user_id
        item.review_comment = (review_comment or "").strip() or None
        item.reviewed_at = datetime.now(timezone.utc)
        if approve:
            # 原始文档不删除；审核通过只创建整合知识，管理员可明确选择归档来源文档。
            item.merged_document_id = self._create_merged_document(item, reviewer).document_id
            if archive_sources:
                self._archive_source_documents(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def source_documents(self, item: KnowledgeMergeSuggestion) -> list[Document]:
        documents: list[Document] = []
        for document_id in self._source_ids(item):
            document = self.db.get(Document, document_id)
            if document is not None:
                documents.append(document)
        return documents

    def _visible_documents(self, user: AuthenticatedUser) -> list[Document]:
        documents = self.db.execute(
            select(Document).where(
                Document.document_status == "active",
                Document.parse_status == "succeeded",
                Document.content_text.is_not(None),
            )
        ).scalars().all()
        visible: list[Document] = []
        for document in documents:
            if not (document.content_text or "").strip():
                continue
            if document.owner_user_id == user.user_id or self.access.can_access_document(document, user).can_access:
                visible.append(document)
        return visible

    def _vector_candidate_pairs(self, documents: list[Document]) -> dict[tuple[str, str], float]:
        """Use stored BGE vectors and pgvector cosine distance to discover document pairs."""
        document_ids = [document.document_id for document in documents]
        if len(document_ids) < 2:
            return {}
        rows = self.db.execute(
            select(DocumentChunk.document_id, ChunkEmbedding.vector)
            .join(ChunkEmbedding, ChunkEmbedding.chunk_id == DocumentChunk.chunk_id)
            .where(DocumentChunk.document_id.in_(document_ids))
            .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
        ).all()

        representative_vectors: dict[str, list[list[float]]] = {}
        for document_id, vector in rows:
            bucket = representative_vectors.setdefault(str(document_id), [])
            if len(bucket) < 3:
                bucket.append(list(vector))

        pair_scores: dict[tuple[str, str], float] = {}
        for source_id, vectors in representative_vectors.items():
            for vector in vectors:
                nearest = self.db.execute(
                    select(
                        DocumentChunk.document_id,
                        func.min(ChunkEmbedding.vector.cosine_distance(vector)).label("distance"),
                    )
                    .join(ChunkEmbedding, ChunkEmbedding.chunk_id == DocumentChunk.chunk_id)
                    .where(
                        DocumentChunk.document_id.in_(document_ids),
                        DocumentChunk.document_id != source_id,
                    )
                    .group_by(DocumentChunk.document_id)
                    .order_by("distance")
                    .limit(8)
                ).all()
                for target_id, distance in nearest:
                    pair = tuple(sorted((source_id, str(target_id))))
                    similarity = max(0.0, min(1.0, 1.0 - float(distance or 0.0)))
                    pair_scores[pair] = max(pair_scores.get(pair, 0.0), similarity)
        return pair_scores

    def _fallback_candidate_pairs(self, documents: list[Document]) -> dict[tuple[str, str], float]:
        pairs: dict[tuple[str, str], float] = {}
        for index, left in enumerate(documents):
            for right in documents[index + 1 :]:
                lexical_score = self._lexical_similarity(left, right)
                if lexical_score > 0:
                    pairs[tuple(sorted((left.document_id, right.document_id)))] = lexical_score
        return pairs

    def _combined_similarity(self, left: Document, right: Document, semantic_score: float) -> tuple[float, str]:
        lexical_score = self._lexical_similarity(left, right)
        score = min(1.0, semantic_score * 0.8 + lexical_score * 0.2)
        reason = (
            f"BGE-m3 向量经 pgvector 计算的语义相似度为 {semantic_score:.2f}；"
            f"标题、类别和关键词辅助相似度为 {lexical_score:.2f}；综合相似度为 {score:.2f}。"
        )
        return score, reason

    def _lexical_similarity(self, left: Document, right: Document) -> float:
        left_tokens = self._tokens(" ".join([left.file_name, left.knowledge_category or "", left.content_text or ""]))
        right_tokens = self._tokens(" ".join([right.file_name, right.knowledge_category or "", right.content_text or ""]))
        if not left_tokens or not right_tokens:
            return 0.0
        overlap = left_tokens & right_tokens
        score = len(overlap) / max(len(left_tokens | right_tokens), 1)
        if left.knowledge_category and left.knowledge_category == right.knowledge_category:
            score += 0.15
        if self._tokens(left.file_name) & self._tokens(right.file_name):
            score += 0.1
        return min(score, 1.0)

    def _build_merge_draft(self, left: Document, right: Document, similarity_score: float) -> dict[str, str]:
        prompt = {
            "task": "对两份企业知识进行去重、冲突识别和重新组织，生成供管理员审核的整合草稿。不要编造来源中没有的公司制度。",
            "requirements": [
                "删除重复表达，但保留所有互补信息",
                "冲突内容不能擅自裁决，必须列入 conflicts",
                "merged_content 使用 Markdown，并在相关段落标注 [来源1] 或 [来源2]",
                "source_attributions 必须标明每个章节使用了哪些 source_ids",
                "输出只是草稿，不能宣称已经审核通过",
            ],
            "output_schema": {
                "title": "整合标题",
                "category": "知识类别",
                "outline": ["章节标题"],
                "merged_content": "带 [来源1]/[来源2] 标记的 Markdown 正文",
                "conflicts": [{"topic": "冲突主题", "detail": "冲突描述", "recommendation": "待管理员确认事项"}],
                "source_attributions": [{"section": "章节", "source_ids": ["document_id"]}],
            },
            "similarity_score": similarity_score,
            "sources": [
                {"label": "来源1", "document_id": left.document_id, "file_name": left.file_name, "content": self._preview(left.content_text, 6000)},
                {"label": "来源2", "document_id": right.document_id, "file_name": right.file_name, "content": self._preview(right.content_text, 6000)},
            ],
        }
        result = self.deepseek.complete_json(
            "你是企业知识整合 Agent。只输出 JSON。必须保留来源标记，冲突交给管理员，不得自动发布或删除原文档。",
            prompt,
            temperature=0.1,
            timeout=90.0,
        )
        if result:
            normalized = self._normalize_ai_draft(result, left, right)
            if normalized is not None:
                return normalized
        return self._fallback_merge_draft(left, right)

    def _normalize_ai_draft(self, result: dict[str, object], left: Document, right: Document) -> dict[str, str] | None:
        title = str(result.get("title") or "").strip()
        content = str(result.get("merged_content") or "").strip()
        if not title or not content:
            return None
        if "[来源1]" not in content or "[来源2]" not in content:
            content += self._source_appendix(left, right)
        outline = result.get("outline") or []
        outline_text = "\n".join(f"{index + 1}. {item}" for index, item in enumerate(outline)) if isinstance(outline, list) else str(outline)
        conflicts = result.get("conflicts") if isinstance(result.get("conflicts"), list) else []
        attributions = result.get("source_attributions") if isinstance(result.get("source_attributions"), list) else []
        if not attributions:
            attributions = [
                {"section": "来源1", "source_ids": [left.document_id]},
                {"section": "来源2", "source_ids": [right.document_id]},
            ]
        return {
            "suggested_title": title[:255],
            "suggested_category": str(result.get("category") or left.knowledge_category or right.knowledge_category or "整合知识")[:128],
            "suggested_outline": outline_text,
            "suggested_content": content,
            "generation_method": "deepseek",
            "conflict_notes": json.dumps(conflicts, ensure_ascii=False),
            "source_attributions": json.dumps(attributions, ensure_ascii=False),
        }

    def _fallback_merge_draft(self, left: Document, right: Document) -> dict[str, str]:
        title = self._suggest_title(left, right)
        outline = self._suggest_outline(left, right)
        content = "\n\n".join([
            f"# {title}",
            "> 该内容由规则 fallback 生成，仅作为管理员编辑起点。",
            f"## {left.file_name} [来源1]\n{self._preview(left.content_text)}",
            f"## {right.file_name} [来源2]\n{self._preview(right.content_text)}",
            "## 待确认冲突\n规则模式无法可靠判断事实冲突，请管理员对照原文确认。",
            self._source_appendix(left, right),
        ])
        attributions = [
            {"section": left.file_name, "source_ids": [left.document_id]},
            {"section": right.file_name, "source_ids": [right.document_id]},
        ]
        conflicts = [{"topic": "人工确认", "detail": "DeepSeek 不可用，未自动识别冲突", "recommendation": "请管理员对照来源文档审核"}]
        return {
            "suggested_title": title,
            "suggested_category": left.knowledge_category or right.knowledge_category or "整合知识",
            "suggested_outline": outline,
            "suggested_content": content,
            "generation_method": "rule_fallback",
            "conflict_notes": json.dumps(conflicts, ensure_ascii=False),
            "source_attributions": json.dumps(attributions, ensure_ascii=False),
        }

    def _source_appendix(self, left: Document, right: Document) -> str:
        return (
            "\n\n## 来源文档\n"
            f"- [来源1] {left.file_name} ({left.document_id})\n"
            f"- [来源2] {right.file_name} ({right.document_id})"
        )

    def _find_existing(self, source_ids: list[str]) -> KnowledgeMergeSuggestion | None:
        raw = json.dumps(source_ids, ensure_ascii=False)
        return self.db.execute(
            select(KnowledgeMergeSuggestion).where(
                KnowledgeMergeSuggestion.source_document_ids == raw,
                KnowledgeMergeSuggestion.status == "pending",
            )
        ).scalar_one_or_none()

    def _tokens(self, text: str) -> set[str]:
        text = text.lower()
        words = set(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2,}", text))
        compact = re.sub(r"\s+", "", text)
        for index in range(max(0, len(compact) - 1)):
            gram = compact[index : index + 2]
            if re.search(r"[\u4e00-\u9fff]", gram):
                words.add(gram)
        return {word for word in words if len(word) >= 2}

    def _suggest_title(self, left: Document, right: Document) -> str:
        category = left.knowledge_category or right.knowledge_category
        if category:
            return f"{category}整合知识"
        common = sorted(self._tokens(left.file_name) & self._tokens(right.file_name))
        return f"{common[0]}整合知识" if common else "知识整合草稿"

    def _suggest_outline(self, left: Document, right: Document) -> str:
        return "\n".join([
            "1. 背景与适用场景",
            "2. 关键概念与制度依据",
            "3. 操作流程",
            "4. 冲突与待确认事项",
            "5. 来源文档",
        ])

    def _preview(self, text: str | None, limit: int = 2500) -> str:
        content = (text or "").strip()
        return content[:limit] if content else "暂无可用正文。"

    def _source_ids(self, item: KnowledgeMergeSuggestion) -> list[str]:
        try:
            parsed = json.loads(item.source_document_ids)
        except Exception:
            return []
        return [str(value) for value in parsed if str(value)]

    def _admin_can_view(self, item: KnowledgeMergeSuggestion, user: AuthenticatedUser) -> bool:
        if not {"admin", "reviewer"}.intersection(set(user.roles)):
            return False
        return all(not (document.knowledge_space == "personal" and document.owner_user_id != user.user_id) for document in self.source_documents(item))

    def _can_review(self, item: KnowledgeMergeSuggestion, user: AuthenticatedUser, allow_admin: bool) -> bool:
        documents = self.source_documents(item)
        if documents and all(document.owner_user_id == user.user_id for document in documents):
            return True
        if allow_admin and {"admin", "reviewer"}.intersection(set(user.roles)):
            return all(not (document.knowledge_space == "personal" and document.owner_user_id != user.user_id) for document in documents)
        return False

    def _create_merged_document(self, item: KnowledgeMergeSuggestion, reviewer: AuthenticatedUser) -> Document:
        from app.services.knowledge_service import KnowledgeService

        documents = self.source_documents(item)
        owner_ids = {document.owner_user_id for document in documents if document.owner_user_id}
        owner_user_id = next(iter(owner_ids)) if len(owner_ids) == 1 and all(document.knowledge_space == "personal" for document in documents) else reviewer.user_id
        payload = ManualKnowledgeCreate(
            title=item.suggested_title,
            content=item.suggested_content,
            knowledge_category=item.suggested_category or "整合知识",
            allowed_job_categories="",
            business_purpose="整合相似知识，减少重复知识库文档",
            tags="知识整合,相似知识",
        )
        return KnowledgeService(self.db).create_manual_knowledge(payload, owner_user_id=owner_user_id)

    def _archive_source_documents(self, item: KnowledgeMergeSuggestion) -> None:
        for document in self.source_documents(item):
            document.document_status = "archived"
            metadata = self.db.execute(
                select(KnowledgeMetadata).where(KnowledgeMetadata.document_id == document.document_id)
            ).scalar_one_or_none()
            if metadata is not None:
                metadata.status = "archived"
                metadata.is_archived = True
