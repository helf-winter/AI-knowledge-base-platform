from __future__ import annotations

import hashlib
import re
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundAppError, ValidationAppError
from app.models.core import KnowledgeMetadata, TaskRecord
from app.models.flywheel import KnowledgeGap
from app.schemas.flywheel import KnowledgeGapCreate, KnowledgeGapReview


class KnowledgeFlywheelService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_gap(self, payload: KnowledgeGapCreate) -> KnowledgeGap:
        gap = KnowledgeGap(
            gap_id=str(uuid.uuid4()),
            query_text=payload.query_text,
            session_id=payload.session_id,
            user_id=payload.user_id,
            answer_id=payload.answer_id,
            issue_type=payload.issue_type,
            confidence=payload.confidence,
            evidence=payload.evidence,
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
            if confidence >= min_confidence:
                continue
            existing = self.db.execute(
                select(KnowledgeGap).where(
                    KnowledgeGap.session_id == turn.session_id,
                    KnowledgeGap.query_text == turn.query_text,
                )
            ).scalar_one_or_none()
            if existing is not None:
                continue
            self.create_gap(
                KnowledgeGapCreate(
                    query_text=turn.query_text,
                    session_id=turn.session_id,
                    user_id=turn.user_id,
                    answer_id=getattr(turn, "turn_id", None),
                    issue_type="low_confidence_answer",
                    confidence=confidence,
                    evidence=refs,
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
