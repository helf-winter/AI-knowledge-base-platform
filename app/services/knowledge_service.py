from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.agents.expert_agent import ExpertAgent
from app.core.config import get_settings
from app.core.exceptions import ValidationAppError
from app.core.skills import SkillRegistry
from app.models.conversation import ConversationTurn
from app.models.core import KnowledgeMetadata, TaskRecord
from app.models.document import Document, DocumentChunk, Feedback
from app.models.vector import ChunkEmbedding
from app.schemas.flywheel import KnowledgeGapCreate
from app.services.conversation import ConversationService
from app.services.embedding import fake_embedding
from app.services.flywheel import KnowledgeFlywheelService
from app.services.parsers import chunk_text, extract_text_from_bytes
from app.services.search import HybridRetriever
from app.services.storage import calculate_sha256, save_local_temp
from app.services.task_service import TaskService
from app.services.knowledge_admin import KnowledgeAdminService
from app.services.agent_recommender import AgentRecommender

settings = get_settings()


@dataclass
class SearchHit:
    chunk: DocumentChunk
    score: float
    content: str | None = None
    can_access: bool = True
    need_apply: bool = False
    access_reason: str | None = None


class KnowledgeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.retriever = HybridRetriever(db)
        self.flywheel = KnowledgeFlywheelService(db)
        self.conversation = ConversationService(db)
        self.skills = SkillRegistry(db)
        self.expert_agent = ExpertAgent(db)
        self.tasks = TaskService(db)
        self.agent_recommender = AgentRecommender(db)

    def list_documents(self, limit: int = 100, offset: int = 0) -> list[Document]:
        stmt = select(Document).order_by(Document.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def get_document(self, document_id: str) -> Document | None:
        stmt = select(Document).where(Document.document_id == document_id).options(selectinload(Document.chunks))
        return self.db.execute(stmt).scalar_one_or_none()

    def delete_document(self, document_id: str) -> Document:
        document = self.get_document(document_id)
        if document is None:
            raise ValidationAppError("文档不存在")
        self.db.delete(document)
        self.db.commit()
        return document

    def search(self, query: str, top_k: int = 5, user_id: str | None = None) -> list[SearchHit]:
        if not query.strip():
            raise ValidationAppError("query 不能为空")
        skill_result = self.skills.knowledge_search().execute(query=query, top_k=top_k, user_id=user_id)
        results = skill_result.output.get("results", [])
        hits: list[SearchHit] = []
        for item in results:
            chunk = self.db.get(DocumentChunk, item["chunk_id"])
            if chunk is None:
                continue
            hits.append(
                SearchHit(
                    chunk=chunk,
                    score=float(item.get("score") or 0.0),
                    content=item.get("content"),
                    can_access=bool(item.get("can_access", True)),
                    need_apply=bool(item.get("need_apply", False)),
                    access_reason=item.get("access_reason"),
                )
            )
        return hits

    def list_tasks(self, status: str | None = None) -> list[TaskRecord]:
        return self.tasks.list_tasks(status=status)

    def upload_document(self, file_name: str, content: bytes, owner_user_id: str | None = None) -> Document:
        if not file_name:
            raise ValidationAppError("文件名不能为空")
        if not content:
            raise ValidationAppError("文件内容不能为空")

        checksum = calculate_sha256(content)
        exists = self.db.execute(select(Document).where(Document.checksum == checksum, Document.file_name == file_name)).scalar_one_or_none()
        if exists:
            return exists

        storage_path = save_local_temp(file_name, content)
        document = Document(
            document_id=str(uuid.uuid4()),
            owner_user_id=owner_user_id,
            file_name=file_name,
            file_type=file_name.rsplit(".", 1)[-1].lower(),
            file_size=len(content),
            storage_path=storage_path,
            checksum=checksum,
            parse_status="processing",
            visibility="private",
            visibility_type="private",
            knowledge_space="personal",
            visibility_scope="owner",
            publish_status="none",
            is_public=False,
            content_text=None,
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

        task = self.tasks.create_task("parse_document", related_document_id=document.document_id)
        try:
            self.tasks.mark_running(task.task_id)
            self._process_document(document, content)
            self.tasks.mark_succeeded(task.task_id)
            self._ensure_metadata(document)
        except Exception as exc:
            self.tasks.mark_failed(task.task_id, str(exc))
            raise
        return document

    def _process_document(self, document: Document, content: bytes) -> None:
        try:
            text = extract_text_from_bytes(document.file_name, content)
            document.content_text = text
            chunks = chunk_text(text, settings.chunk_size_tokens, settings.chunk_overlap_tokens)
            if not chunks:
                raise ValidationAppError("未能从文档中提取有效内容")

            existing_hashes = {
                row[0]
                for row in self.db.execute(
                    select(DocumentChunk.content_hash).where(DocumentChunk.document_id == document.document_id)
                ).all()
            }

            for idx, chunk in enumerate(chunks):
                content_hash = calculate_sha256(chunk.encode("utf-8"))
                if content_hash in existing_hashes:
                    continue
                emb = fake_embedding(chunk)
                doc_chunk = DocumentChunk(
                    chunk_id=str(uuid.uuid4()),
                    document_id=document.document_id,
                    chunk_index=idx,
                    parent_section_id=None,
                    content=chunk,
                    token_count=len(chunk.split()),
                    overlap_count=settings.chunk_overlap_tokens if idx > 0 else 0,
                    page_start=idx + 1,
                    page_end=idx + 1,
                    content_hash=content_hash,
                    language="zh",
                    embedding_json=None,
                )
                self.db.add(doc_chunk)
                self.db.flush()
                self.db.add(
                    ChunkEmbedding(
                        embedding_id=str(uuid.uuid4()),
                        chunk_id=doc_chunk.chunk_id,
                        embedding_model="bge-m3",
                        dimension=len(emb),
                        vector=emb,
                    )
                )
                existing_hashes.add(content_hash)

            document.parse_status = "succeeded"
            self.db.commit()
        except Exception:
            document.parse_status = "failed"
            self.db.commit()
            raise

    def _ensure_metadata(self, document: Document) -> None:
        """Create a reviewable metadata row after successful ingestion.

        This keeps the upload -> parse -> governance loop connected out of the box.
        """
        existing = self.db.execute(
            select(KnowledgeMetadata).where(KnowledgeMetadata.document_id == document.document_id)
        ).scalar_one_or_none()
        if existing is not None:
            return

        title = document.file_name.rsplit(".", 1)[0] if "." in document.file_name else document.file_name
        self.db.add(
            KnowledgeMetadata(
                knowledge_id=str(uuid.uuid4()),
                document_id=document.document_id,
                title=title,
                author=None,
                knowledge_type="document",
                version="v1.0.0",
                status="reviewing",
                source_type="upload",
                acl_json=None,
            )
        )
        self.db.commit()

    def answer(
        self,
        query: str,
        top_k: int = 5,
        session_id: str | None = None,
        user_id: str | None = None,
        trace_id: str | None = None,
        agent_id: str | None = None,
    ) -> tuple[str, list[SearchHit], float, list[str], str | None, str | None, str | None]:
        hits = self.search(query=query, top_k=top_k, user_id=user_id)
        recommendation = self.agent_recommender.recommend(query, agent_id=agent_id)
        if not hits:
            answer = "未找到相关知识，请尝试补充或重新表述问题。"
            if recommendation:
                answer += f"\n\n建议你试试：{recommendation.agent_name}。{recommendation.reason}"
            if session_id:
                self.conversation.create_turn(
                    payload=self._make_turn_payload(session_id, user_id, query, answer, 0.0, [], trace_id)
                )
            return answer, [], 0.0, [], recommendation.agent_id if recommendation else None, recommendation.agent_name if recommendation else None, recommendation.reason if recommendation else None

        refs = [f"{h.chunk.document.file_name}#chunk-{h.chunk.chunk_index}" for h in hits]
        answer, refs_from_agent, _traces = self.expert_agent.answer(question=query, top_k=top_k, user_id=user_id)
        if refs_from_agent:
            refs = refs_from_agent

        confidence = min(0.95, sum(h.score for h in hits) / max(len(hits), 1))
        if confidence < 0.45:
            try:
                self.flywheel.create_gap(
                    KnowledgeGapCreate(
                        query_text=query,
                        user_id=user_id,
                        issue_type="low_confidence_answer",
                        confidence=confidence,
                        evidence="retrieval confidence below threshold",
                        answer_id=None,
                        session_id=session_id,
                    )
                )
            except Exception:
                self.db.rollback()
        if recommendation:
            answer = f"{answer}\n\n建议你试试：{recommendation.agent_name}。{recommendation.reason}"
        if session_id:
            self.conversation.create_turn(
                payload=self._make_turn_payload(session_id, user_id, query, answer, confidence, refs, trace_id)
            )
        return answer, hits, confidence, refs, recommendation.agent_id if recommendation else None, recommendation.agent_name if recommendation else None, recommendation.reason if recommendation else None

    def stream_answer(self, query: str, top_k: int = 5, user_id: str | None = None, casual: bool = False):
        """Return a stream iterator together with references and traces."""
        return self.expert_agent.stream_answer(question=query, top_k=top_k, user_id=user_id, casual=casual)

    def expand_knowledge_from_answer(self, query: str, answer: str, user_id: str | None = None, target_document_id: str | None = None, threshold: float = 0.25) -> dict[str, str | None]:
        content = self._build_expansion_content(query, answer)
        target_document = self.get_document(target_document_id) if target_document_id else None
        if target_document is not None:
            document = target_document
            action = "append"
            title = document.file_name
        else:
            hits = self.search(query=query, top_k=1, user_id=user_id)
            best_hit = hits[0] if hits else None
            if best_hit and best_hit.score >= threshold:
                document = best_hit.chunk.document
                action = "append"
                title = document.file_name
            else:
                document = self._create_generated_document(query, content, owner_user_id=user_id)
                action = "create"
                title = document.file_name

        chunk = self._append_chunk(document, content)
        if document.content_text:
            if content not in document.content_text:
                document.content_text = f"{document.content_text.rstrip()}\n\n{content}"
        else:
            document.content_text = content
        document.parse_status = "succeeded"

        metadata = self.db.execute(select(KnowledgeMetadata).where(KnowledgeMetadata.document_id == document.document_id)).scalar_one_or_none()
        if metadata is None:
            metadata = KnowledgeMetadata(
                knowledge_id=str(uuid.uuid4()),
                document_id=document.document_id,
                title=title.rsplit(".", 1)[0],
                author=None,
                knowledge_type="ai_expansion",
                version="v1.0.0",
                status="available",
                source_type="ai_expand",
                acl_json=None,
            )
            self.db.add(metadata)
        else:
            metadata.status = "available"
            if metadata.knowledge_type == "document":
                metadata.knowledge_type = "document_ai_enriched"

        vector = fake_embedding(content)
        self.db.add(ChunkEmbedding(
            embedding_id=str(uuid.uuid4()),
            chunk_id=chunk.chunk_id,
            embedding_model="bge-m3",
            dimension=len(vector),
            vector=vector,
        ))
        self.db.commit()
        self.db.refresh(document)
        self.db.refresh(metadata)
        return {
            "document_id": document.document_id,
            "knowledge_id": metadata.knowledge_id,
            "action": action,
            "title": metadata.title,
        }

    def _build_expansion_content(self, query: str, answer: str) -> str:
        return (
            f"# AI 补充知识：{query.strip()}\n\n"
            f"## 用户问题\n{query.strip()}\n\n"
            f"## 推荐答案\n{answer.strip()}\n\n"
            "## 来源说明\n该内容由问答助手在知识库未充分覆盖时生成，并由用户确认扩充。"
        )

    def _create_generated_document(self, query: str, content: str, owner_user_id: str | None = None) -> Document:
        doc_id = str(uuid.uuid4())
        title = self._safe_generated_title(query)
        encoded = content.encode("utf-8")
        document = Document(
            document_id=doc_id,
            owner_user_id=owner_user_id,
            file_name=f"{title}.md",
            file_type="md",
            file_size=len(encoded),
            storage_path=f"generated://knowledge-expansion/{doc_id}.md",
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
        return document

    def _append_chunk(self, document: Document, content: str) -> DocumentChunk:
        next_index = self.db.execute(
            select(func.coalesce(func.max(DocumentChunk.chunk_index), -1)).where(DocumentChunk.document_id == document.document_id)
        ).scalar_one() + 1
        chunk = DocumentChunk(
            chunk_id=str(uuid.uuid4()),
            document_id=document.document_id,
            chunk_index=int(next_index),
            content=content,
            token_count=max(1, len(content.split())),
            overlap_count=0,
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            language="zh",
            embedding_json=None,
        )
        self.db.add(chunk)
        self.db.flush()
        return chunk

    def _safe_generated_title(self, query: str) -> str:
        title = "".join(ch for ch in query.strip() if ch.isalnum() or ch in (" ", "-", "_")).strip()
        title = title[:40] or "AI补充知识"
        return f"AI补充-{title}"

    def _make_turn_payload(
        self,
        session_id: str,
        user_id: str | None,
        query: str,
        answer: str,
        confidence: float,
        refs: list[str],
        trace_id: str | None = None,
    ):
        from app.schemas.conversation import ConversationTurnCreate

        return ConversationTurnCreate(
            session_id=session_id,
            user_id=user_id,
            query_text=query,
            answer_text=answer,
            confidence=confidence,
            source_refs_json=json.dumps(refs, ensure_ascii=False),
            trace_id=trace_id,
        )

    def record_feedback(
        self,
        session_id: str,
        answer_id: str,
        rating: int,
        is_helpful: bool,
        comment: str | None = None,
        issue_type: str | None = None,
        user_id: str | None = None,
    ) -> Feedback:
        feedback = Feedback(
            feedback_id=str(uuid.uuid4()),
            session_id=session_id,
            answer_id=answer_id,
            rating=rating,
            is_helpful=is_helpful,
            comment=comment,
            issue_type=issue_type,
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback
