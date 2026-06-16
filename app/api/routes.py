from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.learning_agent import LearningAgent
from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.core import AuditLog
from app.schemas.admin import ExpertAgentCreate, ExpertAgentRead, KnowledgeHotnessRead, KnowledgeMetadataCreate, KnowledgeMetadataRead, KnowledgeMetadataUpdate, SkillDescriptor
from app.schemas.audit import AuditLogRead
from app.schemas.auth import CurrentUserRead, LoginRequest, RegisterRequest, TokenResponse
from app.schemas.batch import BatchImportCreate, BatchImportRead
from app.schemas.common import APIResponse
from app.schemas.conversation import ConversationTurnCreate, ConversationTurnRead
from app.schemas.evaluation import EvaluationCaseCreate, EvaluationCaseRead, EvaluationRunCreate, EvaluationRunRead, EvaluationResultRead
from app.schemas.flywheel import KnowledgeGapCreate, KnowledgeGapRecord, KnowledgeGapReview, LearningAnalysisRead
from app.schemas.knowledge import ChatRequest, ChunkItem, DocumentCreateResponse, DocumentDetail, DocumentItem, FeedbackCreate, KnowledgeExpansionRequest, KnowledgeExpansionResponse, SearchRequest, SearchResponse
from app.schemas.observability import AlertEventRead, AlertRuleCreate, AlertRuleRead, MetricSnapshotCreate
from app.schemas.task import TaskRead
from app.services.audit import AuditService
from app.services.auth import AuthService
from app.services.batch_import import BatchImportService
from app.services.conversation import ConversationService
from app.services.evaluation import EvaluationService
from app.services.flywheel import KnowledgeFlywheelService
from app.services.knowledge_admin import KnowledgeAdminService
from app.services.knowledge_service import KnowledgeService
from app.services.observability import ObservabilityService
from app.services.parsers import validate_upload_file
from app.services.task_service import TaskService

router = APIRouter()


def _trace_id_from_request(request: Request | None) -> str:
    if request is None:
        return str(uuid.uuid4())
    return request.headers.get("x-trace-id") or str(uuid.uuid4())


def _handle_app_error(exc: Exception) -> None:
    status_code = 400
    detail = str(exc)
    if getattr(exc, "code", None) == "NOT_FOUND":
        status_code = 404
    elif getattr(exc, "code", None) == "PERMISSION_DENIED":
        status_code = 403
    elif getattr(exc, "code", None) == "VALIDATION_ERROR":
        status_code = 422
    raise HTTPException(status_code=status_code, detail=detail) from exc


def _normalize_session_id(session_id: str | None, user_id: str) -> str:
    if session_id and len(session_id) <= 36:
        return session_id
    if session_id:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{user_id}:{session_id}"))
    return str(uuid.uuid4())


def _looks_like_unknown_answer(answer: str) -> bool:
    lowered = answer.strip().lower()
    markers = [
        "不知道",
        "没有找到",
        "未找到",
        "没有检索到",
        "上下文不足",
        "资料不足",
        "知识库里没有",
        "无法回答",
        "不能回答",
        "not enough",
        "no relevant",
    ]
    return any(marker in lowered for marker in markers)


def _source_documents_for_query(service: KnowledgeService, query: str, user_id: str, answer: str | None = None) -> list[dict[str, str | int]]:
    try:
        hits = service.search(query=query, top_k=5, user_id=user_id)
    except Exception:
        return []
    if not hits:
        return []

    indexed_sources = [
        {
            "source_number": idx,
            "document_id": hit.chunk.document.document_id,
            "file_name": hit.chunk.document.file_name,
            "score": hit.score,
        }
        for idx, hit in enumerate(hits, start=1)
    ]

    cited_numbers: list[int] = []
    if answer:
        seen_numbers: set[int] = set()
        for raw in re.findall(r"\[(\d+)\]", answer):
            number = int(raw)
            if 1 <= number <= len(indexed_sources) and number not in seen_numbers:
                cited_numbers.append(number)
                seen_numbers.add(number)

    if cited_numbers:
        return [
            {
                "source_number": item["source_number"],
                "document_id": item["document_id"],
                "file_name": item["file_name"],
            }
            for item in indexed_sources
            if int(item["source_number"]) in cited_numbers
        ]

    grouped: dict[str, dict[str, object]] = {}
    for item in indexed_sources:
        document_id = str(item["document_id"])
        current = grouped.setdefault(
            document_id,
            {
                "source_number": item["source_number"],
                "document_id": document_id,
                "file_name": item["file_name"],
                "best_score": 0.0,
                "total_score": 0.0,
                "hit_count": 0,
            },
        )
        current["best_score"] = max(float(current["best_score"]), float(item["score"]))
        current["total_score"] = float(current["total_score"]) + float(item["score"])
        current["hit_count"] = int(current["hit_count"]) + 1

    ranked = sorted(
        grouped.values(),
        key=lambda item: (float(item["best_score"]), float(item["total_score"]), int(item["hit_count"])),
        reverse=True,
    )
    best = ranked[0]
    return [{"source_number": int(best["source_number"]), "document_id": str(best["document_id"]), "file_name": str(best["file_name"])}]


@router.post("/auth/register", response_model=APIResponse[TokenResponse])
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    try:
        auth = AuthService(db)
        user, token = auth.register(payload.username, payload.password, payload.display_name, payload.email)
        trace_id = _trace_id_from_request(request)
        AuditService(db).record(user_id=user.user_id, action="register", resource_type="auth", resource_id=user.user_id, trace_id=trace_id, payload={"username": user.username})
        return APIResponse(data=TokenResponse(access_token=token, user_id=user.user_id, username=user.username, display_name=user.display_name, roles=user.roles))
    except Exception as exc:
        _handle_app_error(exc)


@router.post("/auth/login", response_model=APIResponse[TokenResponse])
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    try:
        auth = AuthService(db)
        user, token = auth.login(payload.username, payload.password)
        trace_id = _trace_id_from_request(request)
        AuditService(db).record(user_id=user.user_id, action="login", resource_type="auth", resource_id=user.user_id, trace_id=trace_id, payload={"username": user.username})
        return APIResponse(data=TokenResponse(access_token=token, user_id=user.user_id, username=user.username, display_name=user.display_name, roles=user.roles))
    except Exception as exc:
        _handle_app_error(exc)


@router.get("/auth/me", response_model=APIResponse[CurrentUserRead])
def me(user=Depends(get_current_user)):
    return APIResponse(data=CurrentUserRead(user_id=user.user_id, username=user.username, display_name=user.display_name, email=user.email, roles=user.roles))


@router.post("/documents/upload", response_model=APIResponse[DocumentCreateResponse])
async def upload_document(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    try:
        validate_upload_file(file)
        content = await file.read()
        document = KnowledgeService(db).upload_document(file.filename, content, owner_user_id=user.user_id)
        AuditService(db).record(user_id=user.user_id, action="upload_document", resource_type="document", resource_id=document.document_id, trace_id=_trace_id_from_request(request), payload={"file_name": file.filename, "file_size": len(content)})
        return APIResponse(data=DocumentCreateResponse(document_id=document.document_id, file_name=document.file_name, parse_status=document.parse_status))
    except Exception as exc:
        _handle_app_error(exc)


@router.get("/documents", response_model=APIResponse[list[DocumentItem]])
def list_documents(limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db), _user=Depends(get_current_user)):
    items = KnowledgeService(db).list_documents(limit=limit, offset=offset)
    return APIResponse(data=[DocumentItem(document_id=item.document_id, file_name=item.file_name, file_type=item.file_type, file_size=item.file_size, parse_status=item.parse_status, visibility=item.visibility, created_at=item.created_at.isoformat() if item.created_at else None, updated_at=item.updated_at.isoformat() if item.updated_at else None) for item in items])


@router.get("/documents/{document_id}/raw")
def get_document_raw(document_id: str, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    document = KnowledgeService(db).get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")
    if document.storage_path.startswith("generated://"):
        raise HTTPException(status_code=404, detail="raw file is not available for generated documents")

    file_path = Path(document.storage_path)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="raw file not found")

    media_types = {
        "pdf": "application/pdf",
        "txt": "text/plain; charset=utf-8",
        "md": "text/markdown; charset=utf-8",
        "csv": "text/csv; charset=utf-8",
    }
    return FileResponse(
        path=file_path,
        filename=document.file_name,
        media_type=media_types.get(document.file_type.lower(), "application/octet-stream"),
    )


@router.get("/documents/{document_id}", response_model=APIResponse[DocumentDetail])
def get_document(document_id: str, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    document = KnowledgeService(db).get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")
    return APIResponse(data=DocumentDetail(document_id=document.document_id, file_name=document.file_name, file_type=document.file_type, file_size=document.file_size, parse_status=document.parse_status, visibility=document.visibility, storage_path=document.storage_path, checksum=document.checksum, content_text=document.content_text, created_at=document.created_at.isoformat() if document.created_at else None, updated_at=document.updated_at.isoformat() if document.updated_at else None, chunks=[ChunkItem(chunk_id=chunk.chunk_id, document_id=chunk.document_id, chunk_index=chunk.chunk_index, content=chunk.content, page_start=chunk.page_start, page_end=chunk.page_end, score=None, source_file_name=document.file_name, file_type=document.file_type, updated_at=document.updated_at.isoformat() if document.updated_at else None) for chunk in document.chunks]))


@router.delete("/documents/{document_id}", response_model=APIResponse[dict[str, Any]])
def delete_document(document_id: str, request: Request, db: Session = Depends(get_db), user=Depends(require_roles("admin"))):
    try:
        document = KnowledgeService(db).delete_document(document_id)
        AuditService(db).record(user_id=user.user_id, action="delete_document", resource_type="document", resource_id=document.document_id, trace_id=_trace_id_from_request(request), payload={"file_name": document.file_name})
        return APIResponse(data={"document_id": document_id, "deleted": True})
    except Exception as exc:
        _handle_app_error(exc)


@router.get("/tasks", response_model=APIResponse[list[TaskRead]])
def list_tasks(status: str | None = None, related_document_id: str | None = None, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    items = TaskService(db).list_tasks(status=status, related_document_id=related_document_id)
    return APIResponse(data=[TaskRead(task_id=item.task_id, task_type=item.task_type, related_document_id=item.related_document_id, status=item.status, retry_count=item.retry_count, error_message=item.error_message, created_at=item.created_at.isoformat() if item.created_at else None, updated_at=item.updated_at.isoformat() if item.updated_at else None) for item in items])


@router.get("/flywheel/learning", response_model=APIResponse[dict[str, Any]])
def learning_analysis(status: str = "pending", db: Session = Depends(get_db), _user=Depends(get_current_user)):
    analysis = LearningAgent(db).analyze_gaps(status=status)
    return APIResponse(data=analysis)


@router.post("/flywheel/run", response_model=APIResponse[dict[str, Any]])
def run_flywheel(hours: int = Query(default=24, ge=1, le=168), min_confidence: float = Query(default=0.45, ge=0.0, le=1.0), db: Session = Depends(get_db), user=Depends(require_roles("admin", "reviewer"))):
    service = KnowledgeFlywheelService(db)
    task = service.create_learning_task(hours=hours, min_confidence=min_confidence)
    AuditService(db).record(user_id=user.user_id, action="auto_learning", resource_type="task", resource_id=task.task_id, trace_id=str(uuid.uuid4()), payload={"hours": hours, "min_confidence": min_confidence})
    return APIResponse(data={"task_id": task.task_id, "status": task.status})


@router.post("/tasks/{task_id}/retry", response_model=APIResponse[TaskRead])
def retry_task(task_id: str, db: Session = Depends(get_db), _user=Depends(require_roles("admin", "reviewer"))):
    item = TaskService(db).retry_task(task_id)
    return APIResponse(data=TaskRead(task_id=item.task_id, task_type=item.task_type, related_document_id=item.related_document_id, status=item.status, retry_count=item.retry_count, error_message=item.error_message, created_at=item.created_at.isoformat() if item.created_at else None, updated_at=item.updated_at.isoformat() if item.updated_at else None))


@router.post("/knowledge/search", response_model=APIResponse[SearchResponse])
def search_knowledge(payload: SearchRequest, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    try:
        hits = KnowledgeService(db).search(query=payload.query, top_k=payload.top_k, user_id=payload.user_id)
        results = [ChunkItem(chunk_id=item.chunk.chunk_id, document_id=item.chunk.document_id, chunk_index=item.chunk.chunk_index, content=item.chunk.content, page_start=item.chunk.page_start, page_end=item.chunk.page_end, score=item.score, source_file_name=item.chunk.document.file_name, file_type=item.chunk.document.file_type, updated_at=item.chunk.document.updated_at.isoformat() if item.chunk.document.updated_at else None) for item in hits]
        return APIResponse(data=SearchResponse(query=payload.query, results=results))
    except Exception as exc:
        _handle_app_error(exc)


@router.post("/chat/stream")
def chat_stream(payload: ChatRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    service = KnowledgeService(db)
    trace_id = str(uuid.uuid4())
    session_id = _normalize_session_id(payload.session_id, user.user_id)

    def event_stream():
        try:
            recommendation = service.agent_recommender.recommend(payload.query, agent_id=payload.agent_id)
            expert_stream, refs, _traces = service.stream_answer(query=payload.query, top_k=5, user_id=user.user_id, casual=False)
            expert_answer = "".join(chunk for chunk in expert_stream if chunk)
            should_fallback = (not refs) or _looks_like_unknown_answer(expert_answer)
            answer_stream = None
            visible_refs = refs
            source_documents: list[dict[str, str | int]] = []
            mode = "knowledge"
            can_expand = False

            if should_fallback:
                answer_stream, _general_refs, _general_traces = service.stream_answer(query=payload.query, top_k=5, user_id=user.user_id, casual=True)
                visible_refs = []
                source_documents = []
                mode = "auto_general"
                can_expand = True
            collected = ""

            yield f"data: [TRACE_ID] {trace_id}\n\n"

            if answer_stream is None:
                collected = expert_answer
                if collected:
                    yield f"data: {json.dumps({'delta': collected}, ensure_ascii=False)}\n\n"
            else:
                for chunk in answer_stream:
                    if not chunk:
                        continue
                    collected += chunk
                    yield f"data: {json.dumps({'delta': chunk}, ensure_ascii=False)}\n\n"

            if visible_refs:
                source_documents = _source_documents_for_query(service, payload.query, user.user_id, collected)
            confidence = 0.75 if collected.strip() else 0.0
            hits_count = len(visible_refs)
            ConversationService(db).create_turn(
                ConversationTurnCreate(
                    session_id=session_id,
                    user_id=user.user_id,
                    query_text=payload.query,
                    answer_text=collected.strip() or "未生成回答",
                    confidence=confidence,
                    source_refs_json=json.dumps(source_documents, ensure_ascii=False),
                    trace_id=trace_id,
                )
            )
            AuditService(db).record(
                user_id=user.user_id,
                action="chat_stream",
                resource_type="conversation",
                resource_id=session_id,
                trace_id=trace_id,
                payload={"query": payload.query, "mode": mode, "chunk_count": len(visible_refs), "answer_empty": not bool(collected.strip()), "can_expand": can_expand},
            )
            yield f"data: {json.dumps({'confidence': confidence, 'chunk_count': hits_count, 'trace_id': trace_id, 'session_id': session_id, 'mode': mode, 'can_expand': can_expand, 'expansion_question': '是否扩充该知识内容？' if can_expand else None, 'sources': source_documents, 'recommended_agent_id': recommendation.agent_id if recommendation else None, 'recommended_agent_name': recommendation.agent_name if recommendation else None, 'recommended_reason': recommendation.reason if recommendation else None}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            try:
                db.rollback()
            except Exception:
                pass
            try:
                AuditService(db).record(
                    user_id=user.user_id,
                    action="chat_stream_failed",
                    resource_type="conversation",
                    resource_id=session_id,
                    trace_id=trace_id,
                    payload={"query": payload.query, "error": str(exc)},
                )
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass
            yield f"data: {json.dumps({'error': str(exc), 'trace_id': trace_id}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/feedback", response_model=APIResponse[dict[str, Any]])
def create_feedback(payload: FeedbackCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    feedback = KnowledgeService(db).record_feedback(session_id=payload.session_id, answer_id=payload.answer_id, rating=payload.rating, is_helpful=payload.is_helpful, comment=payload.comment, issue_type=payload.issue_type)
    AuditService(db).record(user_id=user.user_id, action="feedback", resource_type="feedback", resource_id=feedback.feedback_id, trace_id=payload.session_id, payload=payload.model_dump())
    return APIResponse(data={"feedback_id": feedback.feedback_id})


@router.post("/knowledge/expand", response_model=APIResponse[KnowledgeExpansionResponse])
def expand_knowledge(payload: KnowledgeExpansionRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        result = KnowledgeService(db).expand_knowledge_from_answer(query=payload.query, answer=payload.answer, user_id=user.user_id, target_document_id=payload.target_document_id)
        AuditService(db).record(
            user_id=user.user_id,
            action="expand_knowledge",
            resource_type="document",
            resource_id=result["document_id"],
            trace_id=payload.trace_id or str(uuid.uuid4()),
            payload={"query": payload.query, "action": result["action"], "title": result["title"]},
        )
        return APIResponse(data=KnowledgeExpansionResponse(**result))
    except Exception as exc:
        _handle_app_error(exc)


@router.get("/conversation/turns", response_model=APIResponse[list[ConversationTurnRead]])
def list_conversation_turns(session_id: str | None = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    items = ConversationService(db).list_turns(session_id=session_id, user_id=user.user_id)
    return APIResponse(data=[ConversationTurnRead(turn_id=item.turn_id, session_id=item.session_id, user_id=item.user_id, query_text=item.query_text, answer_text=item.answer_text, confidence=item.confidence, source_refs_json=item.source_refs_json, model_name=item.model_name, prompt_version=item.prompt_version, trace_id=item.trace_id, created_at=item.created_at.isoformat() if item.created_at else None) for item in items])


@router.get("/audit/logs", response_model=APIResponse[list[AuditLogRead]])
def list_audit_logs(trace_id: str | None = None, action: str | None = None, resource_type: str | None = None, limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db), user=Depends(get_current_user)):
    stmt = select(AuditLog).where(AuditLog.user_id == user.user_id)
    if trace_id:
        stmt = stmt.where(AuditLog.trace_id == trace_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    items = list(db.execute(stmt.order_by(AuditLog.created_at.desc()).limit(limit)).scalars().all())
    return APIResponse(data=[AuditLogRead(log_id=item.log_id, user_id=item.user_id, action=item.action, resource_type=item.resource_type, resource_id=item.resource_id, trace_id=item.trace_id, payload_json=item.payload_json, created_at=item.created_at.isoformat() if item.created_at else None) for item in items])


@router.get("/admin/knowledge-metadata", response_model=APIResponse[list[KnowledgeMetadataRead]])
def list_knowledge_metadata(status: str | None = None, document_id: str | None = None, include_archived: bool = False, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    items = KnowledgeAdminService(db).list_metadata(status=status, document_id=document_id, include_archived=include_archived)
    return APIResponse(data=[KnowledgeMetadataRead(knowledge_id=item.knowledge_id, document_id=item.document_id, title=item.title, author=item.author, knowledge_type=item.knowledge_type, version=item.version, status=item.status, source_type=item.source_type, acl_json=item.acl_json, is_archived=bool(item.is_archived), deleted_at=item.deleted_at, created_at=item.created_at, updated_at=item.updated_at) for item in items])


@router.get("/admin/skills", response_model=APIResponse[list[SkillDescriptor]])
def list_skills(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    items = KnowledgeAdminService(db).catalog_skills()
    return APIResponse(data=items)


@router.get("/admin/expert-agents", response_model=APIResponse[list[ExpertAgentRead]])
def list_expert_agents(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    items = KnowledgeAdminService(db).list_expert_agents()
    return APIResponse(data=[ExpertAgentRead(agent_id=item.agent_id, name=item.agent_name, description=item.description, knowledge_domain=item.domain_name, knowledge_scope_json=item.knowledge_scope_json, skills_json=getattr(item, "skills_json", None), model_name="deepseek", prompt_version="v1", status=item.status, created_at=item.created_at, updated_at=item.updated_at) for item in items])


@router.post("/admin/expert-agents", response_model=APIResponse[ExpertAgentRead])
def create_expert_agent(payload: ExpertAgentCreate, db: Session = Depends(get_db), _user=Depends(require_roles("admin", "reviewer"))):
    item = KnowledgeAdminService(db).create_expert_agent(payload)
    return APIResponse(data=ExpertAgentRead(agent_id=item.agent_id, name=item.agent_name, description=item.description, knowledge_domain=item.domain_name, knowledge_scope_json=item.knowledge_scope_json, skills_json=getattr(item, "skills_json", None), model_name="deepseek", prompt_version="v1", status=item.status, created_at=item.created_at, updated_at=item.updated_at))


@router.get("/admin/knowledge-hotness", response_model=APIResponse[list[KnowledgeHotnessRead]])
def knowledge_hotness(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db), _user=Depends(require_roles("admin", "reviewer"))):
    items = KnowledgeAdminService(db).hotness_stats(limit=limit)
    return APIResponse(data=items)


@router.post("/admin/knowledge-metadata", response_model=APIResponse[KnowledgeMetadataRead])
def create_knowledge_metadata(payload: KnowledgeMetadataCreate, db: Session = Depends(get_db), _user=Depends(require_roles("admin", "reviewer"))):
    item = KnowledgeAdminService(db).create_metadata(payload)
    return APIResponse(data=KnowledgeMetadataRead(knowledge_id=item.knowledge_id, document_id=item.document_id, title=item.title, author=item.author, knowledge_type=item.knowledge_type, version=item.version, status=item.status, source_type=item.source_type, acl_json=item.acl_json, is_archived=bool(item.is_archived), deleted_at=item.deleted_at, created_at=item.created_at, updated_at=item.updated_at))


@router.put("/admin/knowledge-metadata/{knowledge_id}", response_model=APIResponse[KnowledgeMetadataRead])
def update_knowledge_metadata(knowledge_id: str, payload: KnowledgeMetadataUpdate, db: Session = Depends(get_db), _user=Depends(require_roles("admin", "reviewer"))):
    item = KnowledgeAdminService(db).update_metadata(knowledge_id, payload)
    return APIResponse(data=KnowledgeMetadataRead(knowledge_id=item.knowledge_id, document_id=item.document_id, title=item.title, author=item.author, knowledge_type=item.knowledge_type, version=item.version, status=item.status, source_type=item.source_type, acl_json=item.acl_json, created_at=item.created_at, updated_at=item.updated_at))


@router.post("/admin/knowledge-metadata/{knowledge_id}/review", response_model=APIResponse[KnowledgeMetadataRead])
def review_knowledge_metadata(knowledge_id: str, approve: bool = Query(default=True), db: Session = Depends(get_db), _user=Depends(require_roles("admin", "reviewer"))):
    item = KnowledgeAdminService(db).review_metadata(knowledge_id, approve)
    return APIResponse(data=KnowledgeMetadataRead(knowledge_id=item.knowledge_id, document_id=item.document_id, title=item.title, author=item.author, knowledge_type=item.knowledge_type, version=item.version, status=item.status, source_type=item.source_type, acl_json=item.acl_json, is_archived=bool(item.is_archived), deleted_at=item.deleted_at, created_at=item.created_at, updated_at=item.updated_at))


@router.post("/admin/knowledge-metadata/{knowledge_id}/archive", response_model=APIResponse[KnowledgeMetadataRead])
def archive_knowledge_metadata(knowledge_id: str, db: Session = Depends(get_db), _user=Depends(require_roles("admin", "reviewer"))):
    item = KnowledgeAdminService(db).archive_metadata(knowledge_id)
    return APIResponse(data=KnowledgeMetadataRead(knowledge_id=item.knowledge_id, document_id=item.document_id, title=item.title, author=item.author, knowledge_type=item.knowledge_type, version=item.version, status=item.status, source_type=item.source_type, acl_json=item.acl_json, is_archived=bool(item.is_archived), deleted_at=item.deleted_at, created_at=item.created_at, updated_at=item.updated_at))


@router.delete("/admin/knowledge-metadata/{knowledge_id}", response_model=APIResponse[KnowledgeMetadataRead])
def delete_knowledge_metadata(knowledge_id: str, db: Session = Depends(get_db), _user=Depends(require_roles("admin", "reviewer"))):
    item = KnowledgeAdminService(db).delete_metadata(knowledge_id)
    return APIResponse(data=KnowledgeMetadataRead(knowledge_id=item.knowledge_id, document_id=item.document_id, title=item.title, author=item.author, knowledge_type=item.knowledge_type, version=item.version, status=item.status, source_type=item.source_type, acl_json=item.acl_json, is_archived=bool(item.is_archived), deleted_at=item.deleted_at, created_at=item.created_at, updated_at=item.updated_at))
