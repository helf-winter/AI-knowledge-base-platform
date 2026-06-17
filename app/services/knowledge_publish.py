from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundAppError, PermissionAppError, ValidationAppError
from app.models.core import User
from app.models.document import Document, KnowledgePublishRequest
from app.schemas.knowledge import KnowledgePublishRequestCreate
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
            document.knowledge_space = "public"
            document.visibility = "public"
            document.visibility_type = "public"
            document.visibility_scope = "public"
            document.is_public = True
            document.publish_status = "approved"
            document.knowledge_category = item.target_category
            document.allowed_job_categories = item.allowed_job_categories
        else:
            document.knowledge_space = "personal"
            document.visibility = "private"
            document.visibility_type = "private"
            document.visibility_scope = "owner"
            document.is_public = False
            document.publish_status = "rejected"

        self.db.commit()
        self.db.refresh(item)
        return item

    def get_context(self, item: KnowledgePublishRequest) -> dict[str, object | None]:
        return {
            "requester": self.db.get(User, item.requester_id),
            "document": self.db.get(Document, item.document_id),
        }
