from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.agents.expert_agent import ExpertAgent
from app.agents.review_agent import ReviewAgent
from app.core.config import get_settings
from app.core.exceptions import PermissionAppError, ValidationAppError
from app.core.skills import SkillRegistry
from app.models.conversation import ConversationTurn
from app.models.core import KnowledgeMetadata, TaskRecord
from app.models.document import Document, DocumentChunk, Feedback, PublicKnowledgeRef
from app.models.vector import ChunkEmbedding
from app.schemas.flywheel import KnowledgeGapCreate
from app.schemas.knowledge import ManualKnowledgeCreate
from app.schemas.review import ReviewRequest
from app.services.conversation import ConversationService
from app.services.embedding import EmbeddingService
from app.services.expert_agent_runtime import ExpertAgentContext, ExpertAgentRuntime
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
        self.agent_runtime = ExpertAgentRuntime(db)
        self.embedding = EmbeddingService()

    def list_documents(self, limit: int = 100, offset: int = 0) -> list[Document]:
        stmt = select(Document).order_by(Document.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def get_document(self, document_id: str) -> Document | None:
        stmt = select(Document).where(Document.document_id == document_id).options(selectinload(Document.chunks))
        return self.db.execute(stmt).scalar_one_or_none()

    def delete_document(self, document_id: str) -> Document:
        document = self.get_document(document_id)
        if document is None:
            raise ValidationAppError("document not found")
        self.db.delete(document)
        self.db.commit()
        return document

    def search(self, query: str, top_k: int = 5, user_id: str | None = None, scope: dict[str, Any] | None = None) -> list[SearchHit]:
        if not query.strip():
            raise ValidationAppError("query 涓嶈兘涓虹┖")
        skill_result = self.skills.knowledge_search().execute(query=query, top_k=top_k, user_id=user_id, scope=scope)
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
        document = self.create_upload_record(file_name, content, owner_user_id=owner_user_id, parse_status="queued")
        task = self.tasks.create_task("parse_document", related_document_id=document.document_id)
        threshold = settings.background_parse_threshold_mb * 1024 * 1024
        if len(content) >= threshold:
            self.tasks.mark_queued(task.task_id, "文件较大，已进入后台解析队列")
            self.enqueue_parse_document(document.document_id, task.task_id)
        else:
            self.run_parse_document_task(document.document_id, task.task_id)
        self.db.refresh(document)
        return document

    def create_upload_record(self, file_name: str, content: bytes, owner_user_id: str | None = None, parse_status: str = "queued") -> Document:
        if not file_name:
            raise ValidationAppError("file_name cannot be empty")
        if not content:
            raise ValidationAppError("file content cannot be empty")

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
            parse_status=parse_status,
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
        return document

    def enqueue_parse_document(self, document_id: str, task_id: str) -> None:
        try:
            from app.tasks.jobs import parse_document_task

            parse_document_task.delay(document_id, task_id)
        except Exception as exc:
            self.tasks.mark_failed(task_id, f"鍚庡彴闃熷垪鎶曢€掑け璐ワ細{exc}")
            document = self.get_document(document_id)
            if document is not None:
                document.parse_status = "failed"
                self.db.commit()
            raise

    def run_parse_document_task(self, document_id: str, task_id: str) -> Document:
        document = self.get_document(document_id)
        if document is None:
            self.tasks.mark_failed(task_id, "document not found")
            raise ValidationAppError("document not found")
        if document.storage_path.startswith("generated://"):
            self.tasks.mark_failed(task_id, "generated document does not need parsing")
            raise ValidationAppError("generated document does not need parsing")

        path = Path(document.storage_path)
        if not path.exists():
            self.tasks.mark_failed(task_id, f"raw file not found: {document.storage_path}")
            document.parse_status = "failed"
            self.db.commit()
            raise ValidationAppError("raw file not found")

        try:
            document.parse_status = "processing"
            self.db.commit()
            self.tasks.mark_progress(task_id, "extracting_text", 0, 0, "姝ｅ湪鎻愬彇鏂囨湰")
            self._process_document(document, path.read_bytes(), task_id=task_id)
            self._ensure_metadata(document)
            self.tasks.mark_succeeded(task_id)
            self.db.refresh(document)
            return document
        except Exception as exc:
            self.db.rollback()
            document = self.get_document(document_id)
            if document is not None:
                document.parse_status = "failed"
                self.db.commit()
            self.tasks.mark_failed(task_id, str(exc))
            raise

    def retry_document_parsing(self, document_id: str) -> TaskRecord:
        document = self.get_document(document_id)
        if document is None:
            raise ValidationAppError("document not found")
        task = self.db.execute(
            select(TaskRecord)
            .where(TaskRecord.related_document_id == document_id, TaskRecord.task_type == "parse_document")
            .order_by(TaskRecord.created_at.desc())
        ).scalars().first()
        if task is None:
            task = self.tasks.create_task("parse_document", related_document_id=document_id)
        elif task.status == "running" and not self._is_stale_parse_task(task):
            raise ValidationAppError("parse task is already running")
        else:
            task = self.tasks.retry_task(task.task_id)
        document.parse_status = "queued"
        self.db.commit()
        self.enqueue_parse_document(document.document_id, task.task_id)
        self.db.refresh(task)
        return task

    def _is_stale_parse_task(self, task: TaskRecord) -> bool:
        updated_at = task.updated_at or task.created_at
        if updated_at is None:
            return False
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - updated_at > timedelta(minutes=settings.parse_task_stale_minutes)

    def create_manual_knowledge(self, payload: ManualKnowledgeCreate, owner_user_id: str | None = None) -> Document:
        title = payload.title.strip()
        content = payload.content.strip()
        category = payload.knowledge_category.strip()
        if not title:
            raise ValidationAppError("鏍囬涓嶈兘涓虹┖")
        if not content:
            raise ValidationAppError("正文不能为空")
        if not category:
            raise ValidationAppError("鐭ヨ瘑绫诲埆涓嶈兘涓虹┖")

        full_content = self._build_manual_knowledge_content(payload, title, content, category)
        encoded = full_content.encode("utf-8")
        document_id = str(uuid.uuid4())
        document = Document(
            document_id=document_id,
            owner_user_id=owner_user_id,
            file_name=f"{self._safe_manual_title(title)}.md",
            file_type="md",
            file_size=len(encoded),
            storage_path=f"generated://manual-knowledge/{document_id}.md",
            checksum=hashlib.sha256(encoded).hexdigest(),
            parse_status="succeeded",
            visibility="private",
            visibility_type="private",
            knowledge_space="personal",
            visibility_scope="owner",
            allowed_job_categories=(payload.allowed_job_categories or "").strip() or None,
            knowledge_category=category,
            publish_status="none",
            is_public=False,
            content_text=full_content,
        )
        self.db.add(document)
        self.db.flush()

        chunks = chunk_text(full_content, settings.chunk_size_tokens, settings.chunk_overlap_tokens) or [full_content]
        for idx, chunk in enumerate(chunks):
            content_hash = calculate_sha256(chunk.encode("utf-8"))
            emb = self.embedding.embed_text(chunk)
            doc_chunk = DocumentChunk(
                chunk_id=str(uuid.uuid4()),
                document_id=document.document_id,
                chunk_index=idx,
                parent_section_id=None,
                content=chunk,
                token_count=max(1, len(chunk.split())),
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
                    embedding_model=self.embedding.model_name,
                    dimension=len(emb),
                    vector=emb,
                )
            )

        self.db.add(
            KnowledgeMetadata(
                knowledge_id=str(uuid.uuid4()),
                document_id=document.document_id,
                title=title,
                author=None,
                knowledge_type=category,
                version="v1.0.0",
                status="available",
                source_type="manual",
                acl_json=None,
            )
        )
        self.db.commit()
        self.db.refresh(document)
        return document

    def _build_manual_knowledge_content(self, payload: ManualKnowledgeCreate, title: str, content: str, category: str) -> str:
        lines = [f"# {title}", "", f"知识类别：{category}"]
        if payload.allowed_job_categories and payload.allowed_job_categories.strip():
            lines.append(f"适用人员：{payload.allowed_job_categories.strip()}")
        if payload.business_purpose and payload.business_purpose.strip():
            lines.append(f"业务用途：{payload.business_purpose.strip()}")
        if payload.tags and payload.tags.strip():
            lines.append(f"标签：{payload.tags.strip()}")
        lines.extend(["", "## 正文", content])
        return "\n".join(lines)

    def _safe_manual_title(self, title: str) -> str:
        safe = "".join(ch for ch in title if ch.isalnum() or ch in (" ", "-", "_")).strip()
        return safe[:80] or "鎵嬪姩璁板綍鐭ヨ瘑"

    def _process_document(self, document: Document, content: bytes, task_id: str | None = None) -> None:
        try:
            text = extract_text_from_bytes(document.file_name, content)
            document.content_text = text
            chunks = chunk_text(text, settings.chunk_size_tokens, settings.chunk_overlap_tokens)
            if task_id:
                self.tasks.mark_progress(task_id, "chunking", 0, len(chunks), f"chunked {len(chunks)} knowledge segments")
            if not chunks:
                raise ValidationAppError("鏈兘浠庢枃妗ｄ腑鎻愬彇鏈夋晥鍐呭")

            # 断点续跑：复用已经写入的 chunk，并补齐缺失的 embedding。
            existing_chunks_by_hash = {
                chunk.content_hash: chunk
                for chunk in self.db.execute(
                    select(DocumentChunk).where(DocumentChunk.document_id == document.document_id)
                ).scalars().all()
            }
            existing_embedding_chunk_ids = {
                row[0]
                for row in self.db.execute(
                    select(ChunkEmbedding.chunk_id)
                    .join(DocumentChunk)
                    .where(DocumentChunk.document_id == document.document_id)
                ).all()
            }

            for idx, chunk in enumerate(chunks):
                content_hash = calculate_sha256(chunk.encode("utf-8"))
                existing_chunk = existing_chunks_by_hash.get(content_hash)
                if existing_chunk is not None:
                    self._ensure_chunk_embedding(existing_chunk, chunk, existing_embedding_chunk_ids)
                    if task_id:
                        self.tasks.mark_progress(task_id, "embedding", idx + 1, len(chunks), "复用已存在的知识片段")
                    continue
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
                self._ensure_chunk_embedding(doc_chunk, chunk, existing_embedding_chunk_ids)
                existing_chunks_by_hash[content_hash] = doc_chunk
                if task_id:
                    self.tasks.mark_progress(task_id, "embedding", idx + 1, len(chunks), "正在生成语义向量")

            document.parse_status = "succeeded"
            self.db.commit()
        except Exception:
            self.db.rollback()
            document.parse_status = "failed"
            self.db.commit()
            raise

    def _ensure_chunk_embedding(self, chunk: DocumentChunk, content: str, existing_embedding_chunk_ids: set[str]) -> None:
        if chunk.chunk_id in existing_embedding_chunk_ids:
            return
        vector = self.embedding.embed_text(content)
        self.db.add(
            ChunkEmbedding(
                embedding_id=str(uuid.uuid4()),
                chunk_id=chunk.chunk_id,
                embedding_model=self.embedding.model_name,
                dimension=len(vector),
                vector=vector,
            )
        )
        existing_embedding_chunk_ids.add(chunk.chunk_id)

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
        conversation_context: list[dict[str, str]] | None = None,
    ) -> tuple[str, list[SearchHit], float, list[str], str | None, str | None, str | None]:
        agent_context = self.resolve_agent_context(query=query, agent_id=agent_id)
        hits = self.search(query=query, top_k=top_k, user_id=user_id, scope=agent_context.search_scope() if agent_context else None)
        if not hits:
            answer = "未找到相关知识，请尝试补充或重新表述问题。"
            if agent_context:
                answer += f"\n\n已使用专家：{agent_context.agent_name}。{agent_context.selection_reason}"
            if session_id:
                self.conversation.create_turn(
                    payload=self._make_turn_payload(session_id, user_id, query, answer, 0.0, [], trace_id)
                )
            return answer, [], 0.0, [], agent_context.agent_id if agent_context else None, agent_context.agent_name if agent_context else None, agent_context.selection_reason if agent_context else None

        refs = [f"{h.chunk.document.file_name}#chunk-{h.chunk.chunk_index}" for h in hits]
        answer, refs_from_agent, _traces = self.expert_agent.answer(
            question=query,
            top_k=top_k,
            user_id=user_id,
            agent_context=agent_context,
            conversation_context=conversation_context,
        )
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
        if agent_context:
            answer = f"{answer}\n\n已使用专家：{agent_context.agent_name}。{agent_context.selection_reason}"
        if session_id:
            self.conversation.create_turn(
                payload=self._make_turn_payload(session_id, user_id, query, answer, confidence, refs, trace_id)
            )
        return answer, hits, confidence, refs, agent_context.agent_id if agent_context else None, agent_context.agent_name if agent_context else None, agent_context.selection_reason if agent_context else None

    def resolve_agent_context(self, query: str, agent_id: str | None = None) -> ExpertAgentContext | None:
        return self.agent_runtime.resolve(question=query, agent_id=agent_id)

    def stream_answer(
        self,
        query: str,
        top_k: int = 5,
        user_id: str | None = None,
        casual: bool = False,
        agent_context: ExpertAgentContext | None = None,
        conversation_context: list[dict[str, str]] | None = None,
    ):
        """Return a stream iterator together with references and traces."""
        return self.expert_agent.stream_answer(
            question=query,
            top_k=top_k,
            user_id=user_id,
            casual=casual,
            agent_context=agent_context,
            conversation_context=conversation_context,
        )

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
        if action == "append":
            self._mark_public_refs_need_review(document)
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

        vector = self.embedding.embed_text(content)
        self.db.add(ChunkEmbedding(
            embedding_id=str(uuid.uuid4()),
            chunk_id=chunk.chunk_id,
            embedding_model=self.embedding.model_name,
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

    def _mark_public_refs_need_review(self, document: Document) -> None:
        refs = self.db.execute(
            select(PublicKnowledgeRef).where(
                PublicKnowledgeRef.document_id == document.document_id,
                PublicKnowledgeRef.status == "active",
            )
        ).scalars().all()
        if not refs:
            return
        for ref in refs:
            ref.status = "needs_review"
        document.publish_status = "pending"

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
        title = title[:40] or "AI琛ュ厖鐭ヨ瘑"
        return f"AI琛ュ厖-{title}"

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
        turn = self.db.get(ConversationTurn, answer_id)
        if turn is None or turn.session_id != session_id:
            raise ValidationAppError("问答记录不存在或会话信息不匹配")
        if not user_id or turn.user_id != user_id:
            raise PermissionAppError("只能评价自己的问答记录")

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
        if (not is_helpful) or rating <= 2:
            try:
                review = ReviewAgent(self.db).review(
                    ReviewRequest(
                        review_type="answer_quality",
                        subject={
                            "query": turn.query_text,
                            "answer": turn.answer_text,
                            "confidence": turn.confidence,
                            "mode": "feedback",
                            "has_sources": (turn.source_refs_json or "[]").strip() not in {"", "[]", "null"},
                            "user_feedback": {
                                "rating": rating,
                                "is_helpful": is_helpful,
                                "comment": comment,
                                "issue_type": issue_type,
                            },
                        },
                        context={"session_id": session_id, "answer_id": answer_id},
                    )
                )
                if review.suggestion in {"review", "reject"}:
                    self.flywheel.create_gap(
                        KnowledgeGapCreate(
                            query_text=turn.query_text,
                            session_id=turn.session_id,
                            user_id=user_id,
                            answer_id=turn.turn_id,
                            issue_type=issue_type or "negative_user_feedback",
                            confidence=min(float(turn.confidence or 0.0), 0.3),
                            evidence=json.dumps(review.model_dump(), ensure_ascii=False),
                        )
                    )
            except Exception:
                self.db.rollback()
        return feedback

