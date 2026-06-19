from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.review_agent import ReviewAgent
from app.core.config import get_settings
from app.core.exceptions import NotFoundAppError, ValidationAppError
from app.models.core import KnowledgeMetadata, TaskRecord
from app.models.document import Document, DocumentChunk
from app.models.flywheel import KnowledgeGap
from app.models.vector import ChunkEmbedding
from app.schemas.flywheel import KnowledgeGapCreate, KnowledgeGapReview, LearningGapDraftCreate, LearningGapDraftReview
from app.schemas.knowledge import KnowledgePublishRequestCreate
from app.schemas.review import ReviewRequest
from app.services.auth import AuthenticatedUser
from app.services.embedding import EmbeddingService
from app.services.knowledge_publish import KnowledgePublishService
from app.services.storage import calculate_sha256

settings = get_settings()

class KnowledgeFlywheelService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.embedding = EmbeddingService()

    def create_gap(self, payload: KnowledgeGapCreate) -> KnowledgeGap:
        normalized_question = self.normalize_gap_question(payload.query_text)
        cluster_key = self._cluster_key(payload.query_text, payload.issue_type)
        existing = self.db.execute(
            select(KnowledgeGap).where(
                KnowledgeGap.normalized_question == normalized_question,
                KnowledgeGap.issue_type == payload.issue_type,
                KnowledgeGap.status.in_(["pending", "clustered", "drafted"]),
            )
        ).scalars().first()
        if existing is not None:
            existing.hit_count = int(existing.hit_count or 1) + 1
            existing.confidence = min(float(existing.confidence or 0.0), payload.confidence)
            if payload.evidence:
                existing.evidence = self._append_evidence(existing.evidence, payload.evidence)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        gap = KnowledgeGap(
            gap_id=str(uuid.uuid4()),
            query_text=payload.query_text,
            session_id=payload.session_id,
            user_id=payload.user_id,
            answer_id=payload.answer_id,
            issue_type=payload.issue_type,
            confidence=payload.confidence,
            evidence=payload.evidence,
            normalized_question=normalized_question,
            cluster_key=cluster_key,
            hit_count=1,
            status="pending",
        )
        self.db.add(gap)
        self.db.commit()
        self.db.refresh(gap)
        return gap

    def list_gaps(self, status: str | None = None) -> list[KnowledgeGap]:
        stmt = select(KnowledgeGap)
        if status:
            stmt = stmt.where(KnowledgeGap.status == status)
        stmt = stmt.order_by(KnowledgeGap.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def normalize_gap_question(self, text: str) -> str:
        value = text.strip().lower()
        value = re.sub(r"\s+", "", value)
        value = re.sub(r"[？?。,.，!！；;：:、\"'`~|/\\\-_+=()[\]{}<>《》]", "", value)
        for word in ["请问", "麻烦", "如何", "怎么", "怎样", "我想", "我要", "能否", "可以"]:
            value = value.replace(word, "")
        return value[:120] or text.strip().lower()[:120]

    def review_gap(self, gap_id: str, payload: KnowledgeGapReview) -> KnowledgeGap:
        gap = self._get_gap(gap_id)
        gap.status = "approved" if payload.approved else "rejected"
        if payload.title is not None:
            gap.suggested_title = payload.title
        if payload.content is not None:
            gap.suggested_content = payload.content
        self.db.commit()
        self.db.refresh(gap)
        return gap

    def approve_gap_to_knowledge(self, gap_id: str, title: str, content: str) -> KnowledgeGap:
        if not title.strip():
            raise ValidationAppError("title 不能为空")
        if not content.strip():
            raise ValidationAppError("content 不能为空")
        gap = self._get_gap(gap_id)
        gap.status = "approved"
        gap.suggested_title = title.strip()
        gap.suggested_content = content.strip()
        self.db.commit()
        self.db.refresh(gap)
        return gap

    def generate_gap_draft(self, gap_id: str, payload: LearningGapDraftCreate, user: AuthenticatedUser) -> KnowledgeGap:
        gap = self._get_gap(gap_id)
        if gap.status in {"approved", "rejected", "ignored"}:
            raise ValidationAppError("已完成处理的知识缺口不能重新生成草稿")

        draft = self._ask_deepseek_for_draft(gap, payload) or self._fallback_draft(gap, payload)
        title = str(draft.get("title") or self._build_title(gap.issue_type, [gap.query_text])).strip()[:120]
        content = str(draft.get("draft_content") or "").strip()
        confirmations = draft.get("pending_confirmations") or []
        if isinstance(confirmations, list):
            pending_confirmations = "\n".join(f"- {item}" for item in confirmations if str(item).strip())
        else:
            pending_confirmations = str(confirmations).strip()
        if not pending_confirmations:
            pending_confirmations = "- 适用范围\n- 负责人或审批人\n- 官方入口或文档链接\n- 注意事项"
        if not content:
            content = self._fallback_draft(gap, payload)["draft_content"]

        document = self._ensure_draft_document(gap, title, content, user)
        gap.suggested_title = title
        gap.suggested_content = content
        gap.ai_draft_content = content
        gap.pending_confirmations = pending_confirmations
        gap.draft_document_id = document.document_id
        gap.target_category = payload.target_category.strip()
        gap.allowed_job_categories = payload.allowed_job_categories.strip()
        gap.business_purpose = payload.business_purpose.strip()
        review = ReviewAgent(self.db).review(
            ReviewRequest(
                review_type="learning_gap_draft",
                subject={
                    "query": gap.query_text,
                    "draft_content": content,
                    "pending_confirmations": pending_confirmations.splitlines(),
                    "target_category": payload.target_category,
                    "allowed_job_categories": payload.allowed_job_categories,
                    "business_purpose": payload.business_purpose,
                },
                context={"gap_id": gap.gap_id},
            )
        )
        gap.evidence = self._append_evidence(gap.evidence, json.dumps({"draft_review": review.model_dump()}, ensure_ascii=False))
        gap.status = "drafted"
        self.db.commit()
        self.db.refresh(gap)
        return gap

    def review_gap_draft(self, gap_id: str, payload: LearningGapDraftReview, reviewer: AuthenticatedUser) -> KnowledgeGap:
        gap = self._get_gap(gap_id)
        if gap.status in {"approved", "rejected"}:
            raise ValidationAppError("已审核的知识缺口不能重复审核")
        if not gap.draft_document_id:
            raise ValidationAppError("请先生成知识草稿")

        document = self.db.get(Document, gap.draft_document_id)
        if document is None:
            raise NotFoundAppError("草稿文档不存在")

        gap.review_comment = (payload.review_comment or "").strip() or None
        gap.reviewed_by = reviewer.user_id
        gap.reviewed_at = datetime.now(timezone.utc)

        if not payload.approve:
            gap.status = "rejected"
            document.publish_status = "rejected"
            self.db.commit()
            self.db.refresh(gap)
            return gap

        final_content = (payload.admin_final_content or gap.ai_draft_content or gap.suggested_content or "").strip()
        if not final_content:
            raise ValidationAppError("通过发布前需要填写管理员定稿内容")

        target_category = (payload.target_category or gap.target_category or "").strip()
        allowed_jobs = (payload.allowed_job_categories or gap.allowed_job_categories or "").strip()
        if not target_category:
            raise ValidationAppError("通过发布前需要填写目标分类")
        if not allowed_jobs:
            raise ValidationAppError("通过发布前需要填写可访问人员工作类别")

        gap.admin_final_content = final_content
        gap.target_category = target_category
        gap.allowed_job_categories = allowed_jobs
        self._replace_document_content(document, final_content)

        publish_service = KnowledgePublishService(self.db)
        request = publish_service.create_admin_request(
            KnowledgePublishRequestCreate(
                document_id=document.document_id,
                target_category=target_category,
                allowed_job_categories=allowed_jobs,
                publish_reason=f"自动学习知识缺口审核通过：{gap.query_text[:120]}",
                business_purpose=gap.business_purpose or "补齐企业知识库缺口，提升后续问答命中率",
            ),
            reviewer=reviewer,
        )
        publish_service.review_request(request_id=request.request_id, approve=True, reviewer=reviewer, review_comment=gap.review_comment)
        gap.status = "approved"
        self.db.commit()
        self.db.refresh(gap)
        return gap

    def auto_extract_gaps_from_turns(self, hours: int = 24, min_confidence: float = 0.45) -> int:
        from app.models.conversation import ConversationTurn

        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        turns = list(
            self.db.execute(
                select(ConversationTurn)
                .where(ConversationTurn.created_at >= since)
                .order_by(ConversationTurn.created_at.desc())
            ).scalars().all()
        )
        created = 0
        for turn in turns:
            confidence = float(getattr(turn, "confidence", 0.0) or 0.0)
            refs = getattr(turn, "source_refs_json", None) or "[]"
            has_sources = refs.strip() not in {"", "[]", "null"}
            if confidence >= min_confidence and has_sources:
                continue
            issue_type = "low_confidence_answer" if confidence < min_confidence else "answer_without_sources"
            existing = self.db.execute(
                select(KnowledgeGap).where(
                    KnowledgeGap.session_id == turn.session_id,
                    KnowledgeGap.query_text == turn.query_text,
                )
            ).scalar_one_or_none()
            if existing is not None:
                continue
            review = ReviewAgent(self.db).review(
                ReviewRequest(
                    review_type="answer_quality",
                    subject={
                        "query": turn.query_text,
                        "answer": turn.answer_text,
                        "confidence": confidence,
                        "mode": "auto_learning_scan",
                        "has_sources": has_sources,
                    },
                    context={"session_id": turn.session_id, "answer_id": getattr(turn, "turn_id", None)},
                )
            )
            self.create_gap(
                KnowledgeGapCreate(
                    query_text=turn.query_text,
                    session_id=turn.session_id,
                    user_id=turn.user_id,
                    answer_id=getattr(turn, "turn_id", None),
                    issue_type=issue_type,
                    confidence=confidence,
                    evidence=json.dumps(review.model_dump(), ensure_ascii=False),
                )
            )
            created += 1
        return created

    def cluster_pending_gaps(self) -> int:
        gaps = self.list_gaps(status="pending")
        if not gaps:
            return 0

        grouped: dict[str, list[KnowledgeGap]] = defaultdict(list)
        for gap in gaps:
            key = self._cluster_key(gap.query_text, gap.issue_type)
            grouped[key].append(gap)

        for key, items in grouped.items():
            title = self._build_title(items[0].issue_type, [item.query_text for item in items[:5]])
            content = self._build_content(items)
            for gap in items:
                gap.suggested_title = title
                gap.suggested_content = content
                gap.status = "clustered"

        self.db.commit()
        return len(gaps)

    def generate_knowledge_drafts(self) -> list[KnowledgeMetadata]:
        clustered = list(self.db.execute(select(KnowledgeGap).where(KnowledgeGap.status == "clustered")).scalars().all())
        if not clustered:
            return []

        grouped: dict[str, list[KnowledgeGap]] = defaultdict(list)
        for gap in clustered:
            grouped[self._cluster_key(gap.query_text, gap.issue_type)].append(gap)

        drafts: list[KnowledgeMetadata] = []
        for cluster_key, items in grouped.items():
            representative = items[0]
            title = representative.suggested_title or self._build_title(representative.issue_type, [item.query_text for item in items[:3]])
            content = representative.suggested_content or self._build_content(items)
            doc_id = f"gap-{cluster_key[:24]}"
            existing = self.db.execute(select(KnowledgeMetadata).where(KnowledgeMetadata.document_id == doc_id)).scalar_one_or_none()
            if existing is None:
                item = KnowledgeMetadata(
                    knowledge_id=str(uuid.uuid4()),
                    document_id=doc_id,
                    title=title,
                    author=None,
                    knowledge_type="auto_draft",
                    version="v1.0.0",
                    status="reviewing",
                    source_type="auto_extract",
                    acl_json=None,
                )
                self.db.add(item)
                drafts.append(item)
            else:
                existing.title = title
                existing.status = "reviewing"
                existing.source_type = "auto_extract"
                drafts.append(existing)
            for gap in items:
                gap.status = "drafted"
                gap.suggested_title = title
                gap.suggested_content = content

        self.db.commit()
        for item in drafts:
            self.db.refresh(item)
        return drafts

    def run_auto_learning(self, hours: int = 24, min_confidence: float = 0.45) -> dict[str, int]:
        created = self.auto_extract_gaps_from_turns(hours=hours, min_confidence=min_confidence)
        clustered = self.cluster_pending_gaps()
        drafts = self.generate_knowledge_drafts()
        return {"gaps_created": created, "gaps_clustered": clustered, "drafts_created": len(drafts)}

    def create_learning_task(self, hours: int = 24, min_confidence: float = 0.45) -> TaskRecord:
        task = TaskRecord(
            task_id=str(uuid.uuid4()),
            task_type="auto_learning",
            related_document_id=None,
            status="pending",
            retry_count=0,
            error_message=None,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        self.run_auto_learning(hours=hours, min_confidence=min_confidence)
        task.status = "succeeded"
        self.db.commit()
        self.db.refresh(task)
        return task

    def _ask_deepseek_for_draft(self, gap: KnowledgeGap, payload: LearningGapDraftCreate) -> dict[str, object] | None:
        if not settings.deepseek_api_key:
            return None
        prompt = {
            "task": "你是企业知识管理平台的知识草稿助手。请根据知识缺口生成可编辑草稿，但不要声称未经确认的信息是事实。",
            "output_schema": {
                "title": "简短标题",
                "draft_content": "Markdown 草稿正文",
                "pending_confirmations": ["需要管理员确认的事项"],
                "risk_note": "风险说明",
            },
            "gap": {
                "query_text": gap.query_text,
                "issue_type": gap.issue_type,
                "confidence": gap.confidence,
                "evidence": gap.evidence,
                "hit_count": gap.hit_count,
            },
            "publish_intent": {
                "target_category": payload.target_category,
                "allowed_job_categories": payload.allowed_job_categories,
                "business_purpose": payload.business_purpose,
            },
        }
        request_payload = {
            "model": settings.deepseek_model,
            "messages": [
                {"role": "system", "content": "只输出 JSON，不要输出 Markdown 代码块。AI 只生成草稿，最终发布必须由管理员审核。"},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            "stream": False,
            "temperature": 0.2,
        }
        headers = {"Authorization": f"Bearer {settings.deepseek_api_key}", "Content-Type": "application/json"}
        try:
            response = httpx.post(f"{settings.deepseek_base_url.rstrip('/')}/chat/completions", headers=headers, json=request_payload, timeout=30.0)
            response.raise_for_status()
            content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            return self._parse_json_object(content)
        except Exception:
            return None

    def _parse_json_object(self, content: str) -> dict[str, object] | None:
        text = content.strip()
        if not text:
            return None
        if text.startswith("```"):
            text = text.strip("`").strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()
        try:
            data = json.loads(text)
        except Exception:
            return None
        return data if isinstance(data, dict) else None

    def _fallback_draft(self, gap: KnowledgeGap, payload: LearningGapDraftCreate) -> dict[str, object]:
        title = self._build_title(gap.issue_type, [gap.query_text])
        content = (
            f"# 待补充知识：{gap.query_text.strip()}\n\n"
            "## 问题背景\n"
            "系统发现该问题在问答中未被充分回答，可能代表当前知识库存在缺口。\n\n"
            "## AI 草稿\n"
            "请管理员根据企业实际流程补充标准答案。可以重点确认办理入口、责任人、审批流程、适用范围和注意事项。\n\n"
            "## 建议发布范围\n"
            f"- 目标分类：{payload.target_category.strip()}\n"
            f"- 可访问人员工作类别：{payload.allowed_job_categories.strip()}\n"
            f"- 业务用途：{payload.business_purpose.strip()}\n\n"
            "## 风险说明\n"
            "该内容由规则 fallback 生成，只能作为编辑起点，不能直接作为最终事实发布。"
        )
        return {
            "title": title,
            "draft_content": content,
            "pending_confirmations": ["适用范围", "负责人或审批人", "官方入口或文档链接", "注意事项"],
            "risk_note": "规则 fallback 草稿，需管理员确认。",
        }

    def _ensure_draft_document(self, gap: KnowledgeGap, title: str, content: str, user: AuthenticatedUser) -> Document:
        document = self.db.get(Document, gap.draft_document_id) if gap.draft_document_id else None
        if document is None:
            doc_id = str(uuid.uuid4())
            encoded = content.encode("utf-8")
            document = Document(
                document_id=doc_id,
                owner_user_id=user.user_id,
                file_name=f"自动学习草稿-{self._safe_title(title)}.md",
                file_type="md",
                file_size=len(encoded),
                storage_path=f"generated://learning-gap/{doc_id}.md",
                checksum=hashlib.sha256(encoded).hexdigest(),
                parse_status="succeeded",
                visibility="private",
                visibility_type="private",
                knowledge_space="personal",
                visibility_scope="owner",
                publish_status="none",
                is_public=False,
                content_text=content,
            )
            self.db.add(document)
            self.db.flush()
            self._replace_document_content(document, content)
            self.db.add(
                KnowledgeMetadata(
                    knowledge_id=str(uuid.uuid4()),
                    document_id=document.document_id,
                    title=title,
                    author=user.display_name,
                    knowledge_type="auto_learning_draft",
                    version="v1.0.0",
                    status="reviewing",
                    source_type="auto_learning",
                    acl_json=None,
                )
            )
        else:
            document.file_name = document.file_name or f"自动学习草稿-{self._safe_title(title)}.md"
            document.owner_user_id = document.owner_user_id or user.user_id
            document.knowledge_space = "personal"
            document.visibility = "private"
            document.visibility_type = "private"
            document.visibility_scope = "owner"
            document.is_public = False
            document.publish_status = "none"
            self._replace_document_content(document, content)
        return document

    def _replace_document_content(self, document: Document, content: str) -> None:
        document.content_text = content
        document.file_size = len(content.encode("utf-8"))
        document.checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
        document.parse_status = "succeeded"
        chunks = list(self.db.execute(select(DocumentChunk).where(DocumentChunk.document_id == document.document_id)).scalars().all())
        for chunk in chunks:
            self.db.delete(chunk)
        self.db.flush()
        chunk_text = content.strip() or document.file_name
        chunk = DocumentChunk(
            chunk_id=str(uuid.uuid4()),
            document_id=document.document_id,
            chunk_index=0,
            content=chunk_text,
            token_count=max(1, len(chunk_text.split())),
            overlap_count=0,
            content_hash=calculate_sha256(chunk_text.encode("utf-8")),
            language="zh",
            embedding_json=None,
        )
        self.db.add(chunk)
        self.db.flush()
        vector = self.embedding.embed_text(chunk_text)
        self.db.add(
            ChunkEmbedding(
                embedding_id=str(uuid.uuid4()),
                chunk_id=chunk.chunk_id,
                embedding_model=self.embedding.model_name,
                dimension=len(vector),
                vector=vector,
            )
        )

    def _safe_title(self, title: str) -> str:
        value = "".join(ch for ch in title.strip() if ch.isalnum() or ch in (" ", "-", "_")).strip()
        return (value[:40] or "知识缺口").strip()

    def _append_evidence(self, current: str | None, addition: str) -> str:
        parts = [part for part in [current, addition] if part]
        text = "\n".join(parts)
        return text[-4000:]

    def _build_title(self, issue_type: str, questions: list[str]) -> str:
        base = self._normalize_issue_type(issue_type)
        headline = self._normalize_question(questions[0]) if questions else base
        return f"{base}：{headline[:40]}" if headline else base

    def _build_content(self, items: list[KnowledgeGap]) -> str:
        lines = ["自动提炼知识草稿", "", "相似问题汇总："]
        for idx, gap in enumerate(items[:10], start=1):
            lines.append(f"{idx}. {gap.query_text}")
        lines.extend([
            "",
            "建议说明：",
            "- 这些问题在问答中多次出现，系统判定为高频知识缺口。",
            "- 可补充标准流程、步骤说明或常见问题解答。",
        ])
        return "\n".join(lines)

    def _cluster_key(self, query_text: str, issue_type: str) -> str:
        normalized = self._strip_question_words(self._normalize_question(query_text))
        payload = f"{issue_type}:{normalized}"
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()

    def _normalize_question(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[?？!！。；;,:：\\/\\\-_=+\[\]{}()<>，、\"'`~|]+", " ", text)
        return text

    def _strip_question_words(self, text: str) -> str:
        prefixes = ["请问", "麻烦", "如何", "怎么", "怎样", "请教", "能否", "可以", "为什么", "怎么做", "如何做"]
        for prefix in prefixes:
            if text.startswith(prefix):
                return text[len(prefix):].strip()
        return text

    def _normalize_issue_type(self, issue_type: str) -> str:
        mapping = {
            "low_confidence_answer": "低置信度问题",
            "missing_knowledge": "知识缺口",
            "repeated_question": "重复问题",
        }
        return mapping.get(issue_type, issue_type)

    def _get_gap(self, gap_id: str) -> KnowledgeGap:
        gap = self.db.get(KnowledgeGap, gap_id)
        if gap is None:
            raise NotFoundAppError("knowledge gap not found")
        return gap
