from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.review_agent import ReviewAgent
from app.core.exceptions import NotFoundAppError, PermissionAppError, ValidationAppError
from app.models.core import User
from app.models.document import Document, KnowledgePublishRequest, PublicKnowledgeRef, PublicKnowledgeSuggestion
from app.schemas.knowledge import KnowledgePublishRequestCreate, PublicKnowledgeSuggestionCreate, PublicKnowledgeSuggestionReview
from app.schemas.review import ReviewRequest
from app.services.access_control import DocumentAccessService
from app.services.auth import AuthenticatedUser


class KnowledgePublishService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_request(self, payload: KnowledgePublishRequestCreate, user: AuthenticatedUser) -> KnowledgePublishRequest:
        document = self.db.get(Document, payload.document_id)
        if document is None:
            raise NotFoundAppError("文档不存在")
        if document.owner_user_id != user.user_id:
            raise PermissionAppError("只能提交自己拥有的个人知识")
        if document.knowledge_space != "personal":
            raise ValidationAppError("只有个人知识可以提交到公有知识库")
        if document.publish_status == "pending":
            existed = self.db.execute(
                select(KnowledgePublishRequest).where(
                    KnowledgePublishRequest.document_id == document.document_id,
                    KnowledgePublishRequest.requester_id == user.user_id,
                    KnowledgePublishRequest.status == "pending",
                )
            ).scalar_one_or_none()
            if existed is not None:
                return existed

        request = KnowledgePublishRequest(
            request_id=str(uuid.uuid4()),
            document_id=document.document_id,
            requester_id=user.user_id,
            target_category=payload.target_category.strip(),
            allowed_job_categories=payload.allowed_job_categories.strip(),
            publish_reason=payload.publish_reason.strip(),
            business_purpose=payload.business_purpose.strip(),
            status="pending",
        )
        document.publish_status = "pending"
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        return request

    def create_admin_request(self, payload: KnowledgePublishRequestCreate, reviewer: AuthenticatedUser) -> KnowledgePublishRequest:
        if not {"admin", "reviewer"}.intersection(set(reviewer.roles)):
            raise PermissionAppError("只有管理员可以代为提交自动学习草稿发布申请")
        document = self.db.get(Document, payload.document_id)
        if document is None:
            raise NotFoundAppError("文档不存在")
        if document.knowledge_space != "personal":
            raise ValidationAppError("只有个人知识可以提交到公有知识库")

        existed = self.db.execute(
            select(KnowledgePublishRequest).where(
                KnowledgePublishRequest.document_id == document.document_id,
                KnowledgePublishRequest.status == "pending",
            )
        ).scalar_one_or_none()
        if existed is not None:
            return existed

        request = KnowledgePublishRequest(
            request_id=str(uuid.uuid4()),
            document_id=document.document_id,
            requester_id=document.owner_user_id or reviewer.user_id,
            target_category=payload.target_category.strip(),
            allowed_job_categories=payload.allowed_job_categories.strip(),
            publish_reason=payload.publish_reason.strip(),
            business_purpose=payload.business_purpose.strip(),
            status="pending",
        )
        document.publish_status = "pending"
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        return request

    def list_my_requests(self, user: AuthenticatedUser) -> list[KnowledgePublishRequest]:
        stmt = select(KnowledgePublishRequest).where(KnowledgePublishRequest.requester_id == user.user_id).order_by(KnowledgePublishRequest.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def list_requests(self, status: str | None = None) -> list[KnowledgePublishRequest]:
        stmt = select(KnowledgePublishRequest).order_by(KnowledgePublishRequest.created_at.desc())
        if status:
            stmt = stmt.where(KnowledgePublishRequest.status == status)
        return list(self.db.execute(stmt).scalars().all())

    def get_request(self, request_id: str) -> KnowledgePublishRequest:
        item = self.db.get(KnowledgePublishRequest, request_id)
        if item is None:
            raise NotFoundAppError("发布申请不存在")
        return item

    def build_ai_review(self, request_id: str) -> dict[str, str]:
        item = self.get_request(request_id)
        if item.status != "pending":
            raise ValidationAppError("已审核的发布申请无需再次生成 AI 建议")

        document = self.db.get(Document, item.document_id)
        requester = self.db.get(User, item.requester_id)
        result = ReviewAgent(self.db).review(
            ReviewRequest(
                review_type="knowledge_publish",
                subject={
                    "target_category": item.target_category,
                    "allowed_job_categories": item.allowed_job_categories,
                    "publish_reason": item.publish_reason,
                    "business_purpose": item.business_purpose,
                    "applicant": {
                        "employee_no": getattr(requester, "employee_no", None),
                        "department": getattr(requester, "department", None),
                        "position": getattr(requester, "position", None),
                        "permission_level": getattr(requester, "permission_level", None),
                    },
                },
                context={
                    "document": {
                        "file_name": getattr(document, "file_name", None),
                        "knowledge_space": getattr(document, "knowledge_space", None),
                        "security_level": getattr(document, "security_level", None),
                        "content_preview": (getattr(document, "content_text", None) or "")[:4000],
                    }
                },
            )
        )
        item.ai_suggestion = result.suggestion
        item.ai_risk_level = result.risk_level
        item.ai_reason = result.reason.strip()[:2000]
        self.db.commit()
        self.db.refresh(item)
        return {
            "suggestion": item.ai_suggestion,
            "risk_level": item.ai_risk_level,
            "reason": item.ai_reason,
        }

    def review_request(self, request_id: str, approve: bool, reviewer: AuthenticatedUser, review_comment: str | None = None) -> KnowledgePublishRequest:
        item = self.get_request(request_id)
        if item.status != "pending":
            raise ValidationAppError("已审核的发布申请不能重复审核")
        document = self.db.get(Document, item.document_id)
        if document is None:
            raise NotFoundAppError("申请关联的文档不存在")

        item.status = "approved" if approve else "rejected"
        item.reviewed_by = reviewer.user_id
        item.review_comment = (review_comment or "").strip() or None
        item.reviewed_at = datetime.now(timezone.utc)

        if approve:
            document.publish_status = "approved"
            document.knowledge_category = item.target_category
            self._replace_public_ref(item, document, reviewer)
        else:
            document.publish_status = "rejected"

        self.db.commit()
        self.db.refresh(item)
        return item

    def get_context(self, item: KnowledgePublishRequest) -> dict[str, object | None]:
        return {
            "requester": self.db.get(User, item.requester_id),
            "document": self.db.get(Document, item.document_id),
        }

    def list_public_refs(self, status: str | None = "active") -> list[PublicKnowledgeRef]:
        stmt = select(PublicKnowledgeRef).order_by(PublicKnowledgeRef.created_at.desc())
        if status:
            stmt = stmt.where(PublicKnowledgeRef.status == status)
        return list(self.db.execute(stmt).scalars().all())

    def disable_public_ref(self, ref_id: str, reviewer: AuthenticatedUser) -> PublicKnowledgeRef:
        ref = self.db.get(PublicKnowledgeRef, ref_id)
        if ref is None:
            raise NotFoundAppError("public knowledge reference not found")
        if ref.status != "active":
            raise ValidationAppError("public knowledge reference is not active")
        ref.status = "disabled"
        ref.disabled_by = reviewer.user_id
        ref.disabled_at = datetime.now(timezone.utc)
        document = self.db.get(Document, ref.document_id)
        if document is not None:
            document.publish_status = "rejected"
        self.db.commit()
        self.db.refresh(ref)
        return ref

    def get_public_ref_context(self, ref: PublicKnowledgeRef) -> dict[str, object | None]:
        return {"document": self.db.get(Document, ref.document_id), "owner": self.db.get(User, ref.owner_user_id) if ref.owner_user_id else None}

    def _replace_public_ref(self, item: KnowledgePublishRequest, document: Document, reviewer: AuthenticatedUser) -> PublicKnowledgeRef:
        now = datetime.now(timezone.utc)
        active_refs = self.db.execute(
            select(PublicKnowledgeRef).where(
                PublicKnowledgeRef.document_id == document.document_id,
                PublicKnowledgeRef.status == "active",
            )
        ).scalars().all()
        for ref in active_refs:
            ref.status = "disabled"
            ref.disabled_by = reviewer.user_id
            ref.disabled_at = now

        ref = PublicKnowledgeRef(
            ref_id=str(uuid.uuid4()),
            document_id=document.document_id,
            publish_request_id=item.request_id,
            owner_user_id=document.owner_user_id,
            target_category=item.target_category,
            allowed_job_categories=item.allowed_job_categories,
            status="active",
            created_by=reviewer.user_id,
        )
        self.db.add(ref)
        return ref


class KnowledgeSuggestionService:
    def __init__(self, db: Session, access: DocumentAccessService | None = None) -> None:
        self.db = db
        self.access = access or DocumentAccessService(db)

    def create_suggestion(self, payload: PublicKnowledgeSuggestionCreate, requester: AuthenticatedUser) -> PublicKnowledgeSuggestion:
        document = self.db.get(Document, payload.document_id)
        if document is None:
            raise NotFoundAppError("文档不存在")
        decision = self.access.can_access_document(document, requester)
        if not decision.can_access:
            raise PermissionAppError(decision.reason)
        if not decision.public_ref_id:
            raise ValidationAppError("只能对公有知识提交建议")

        item = PublicKnowledgeSuggestion(
            suggestion_id=str(uuid.uuid4()),
            document_id=document.document_id,
            public_ref_id=decision.public_ref_id,
            requester_id=requester.user_id,
            suggestion_type=payload.suggestion_type.strip(),
            question=payload.question.strip(),
            suggestion=payload.suggestion.strip(),
            business_impact=payload.business_impact.strip(),
            status="pending",
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_my_suggestions(self, requester: AuthenticatedUser) -> list[PublicKnowledgeSuggestion]:
        stmt = select(PublicKnowledgeSuggestion).where(PublicKnowledgeSuggestion.requester_id == requester.user_id).order_by(PublicKnowledgeSuggestion.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def list_suggestions(self, status: str | None = None) -> list[PublicKnowledgeSuggestion]:
        stmt = select(PublicKnowledgeSuggestion).order_by(PublicKnowledgeSuggestion.created_at.desc())
        if status:
            stmt = stmt.where(PublicKnowledgeSuggestion.status == status)
        return list(self.db.execute(stmt).scalars().all())

    def review_suggestion(self, suggestion_id: str, payload: PublicKnowledgeSuggestionReview, reviewer: AuthenticatedUser) -> PublicKnowledgeSuggestion:
        if not {"admin", "reviewer"}.intersection(set(reviewer.roles)):
            raise PermissionAppError("只有管理员或审核员可以处理公有知识建议")
        item = self.db.get(PublicKnowledgeSuggestion, suggestion_id)
        if item is None:
            raise NotFoundAppError("公有知识建议不存在")
        if item.status != "pending":
            raise ValidationAppError("已处理的建议不能重复处理")
        item.status = payload.status
        item.review_comment = payload.review_comment.strip()
        item.reviewed_by = reviewer.user_id
        item.reviewed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_context(self, item: PublicKnowledgeSuggestion) -> dict[str, object | None]:
        return {
            "document": self.db.get(Document, item.document_id),
            "requester": self.db.get(User, item.requester_id),
        }
