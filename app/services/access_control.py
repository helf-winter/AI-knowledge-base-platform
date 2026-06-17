from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import uuid

import httpx
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import NotFoundAppError, PermissionAppError, ValidationAppError
from app.agents.review_agent import ReviewAgent
from app.models.core import Department, User
from app.models.document import AccessRequest, Document, DocumentAccessGrant, PublicKnowledgeRef
from app.schemas.knowledge import AccessRequestCreate
from app.schemas.review import ReviewRequest
from app.services.auth import AuthenticatedUser

settings = get_settings()


@dataclass(frozen=True)
class AccessDecision:
    can_access: bool
    reason: str
    need_apply: bool = False
    public_ref_id: str | None = None
    effective_knowledge_space: str | None = None
    public_ref_status: str | None = None
    public_ref_category: str | None = None


class DocumentAccessService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def can_access_document(self, document: Document, user: AuthenticatedUser) -> AccessDecision:
        if document.document_status != "active":
            return AccessDecision(False, "文档当前不可用", False)

        public_ref = self._active_public_ref(document)
        if public_ref is not None and self._matches_job_category(self._parse_list(public_ref.allowed_job_categories), user):
            return AccessDecision(
                True,
                "公有知识引用可访问",
                public_ref_id=public_ref.ref_id,
                effective_knowledge_space="public",
                public_ref_status=public_ref.status,
                public_ref_category=public_ref.target_category,
            )

        if "admin" in user.roles:
            return AccessDecision(True, "管理员可访问")

        if document.owner_user_id and document.owner_user_id == user.user_id:
            return AccessDecision(True, "文档创建者可访问")

        knowledge_space = (document.knowledge_space or "public").lower()
        if knowledge_space == "personal":
            return AccessDecision(False, "个人知识仅创建者可访问", False)

        if knowledge_space == "department":
            allowed_departments = self._parse_list(document.allowed_departments)
            if allowed_departments and (user.department or "") not in allowed_departments:
                return AccessDecision(False, "部门知识仅指定部门可访问", False)

        if knowledge_space == "public":
            allowed_jobs = self._parse_list(document.allowed_job_categories)
            if allowed_jobs and not self._matches_job_category(allowed_jobs, user):
                return AccessDecision(False, "该公有知识仅对指定工作类别开放", False)
            return AccessDecision(True, "公开知识可访问")

        visibility_type = (document.visibility_type or document.visibility or "private").lower()
        if document.is_public or visibility_type == "public":
            allowed_jobs = self._parse_list(document.allowed_job_categories)
            if allowed_jobs and not self._matches_job_category(allowed_jobs, user):
                return AccessDecision(False, "该公有知识仅对指定工作类别开放", False)
            return AccessDecision(True, "公开知识可访问")

        if self._has_valid_grant(document.document_id, user.user_id):
            return AccessDecision(True, "已获得访问授权")

        allowed_departments = self._parse_list(document.allowed_departments)
        if allowed_departments and (user.department or "") not in allowed_departments:
            return AccessDecision(False, "该文档仅对指定部门开放，需要申请访问", True)

        user_level = int(user.permission_level or 1)
        min_level = int(document.min_permission_level or 1)
        if user_level < min_level:
            return AccessDecision(False, f"权限等级不足，需要 L{min_level} 及以上", True)

        if visibility_type == "private":
            return AccessDecision(False, "私有文档需要申请访问", True)

        return AccessDecision(True, "符合部门和权限等级要求")

    def check_document_access(self, document_id: str, user: AuthenticatedUser) -> tuple[Document, AccessDecision]:
        document = self.db.get(Document, document_id)
        if document is None:
            raise NotFoundAppError("文档不存在")
        return document, self.can_access_document(document, user)

    def require_document_access(self, document_id: str, user: AuthenticatedUser) -> Document:
        document, decision = self.check_document_access(document_id, user)
        if not decision.can_access:
            raise PermissionAppError(decision.reason)
        return document

    def create_access_request(self, payload: AccessRequestCreate, user: AuthenticatedUser) -> AccessRequest:
        document, decision = self.check_document_access(payload.document_id, user)
        if document.knowledge_space == "personal" and document.owner_user_id != user.user_id:
            raise PermissionAppError("个人知识不能申请访问")
        if decision.can_access:
            raise ValidationAppError("你已经可以访问该文档，无需重复申请")
        if not decision.need_apply:
            raise PermissionAppError(decision.reason)

        existed = self.db.execute(
            select(AccessRequest).where(
                AccessRequest.user_id == user.user_id,
                AccessRequest.document_id == document.document_id,
                AccessRequest.status == "pending",
            )
        ).scalar_one_or_none()
        if existed is not None:
            return existed

        request = AccessRequest(
            request_id=str(uuid.uuid4()),
            user_id=user.user_id,
            document_id=document.document_id,
            reason=payload.reason.strip(),
            business_purpose=payload.business_purpose.strip(),
            expected_duration=payload.expected_duration.strip() if payload.expected_duration else None,
            status="pending",
        )
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        return request

    def list_my_requests(self, user: AuthenticatedUser) -> list[AccessRequest]:
        stmt = select(AccessRequest).where(AccessRequest.user_id == user.user_id).order_by(AccessRequest.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def list_requests(self, status: str | None = None) -> list[AccessRequest]:
        stmt = select(AccessRequest).order_by(AccessRequest.created_at.desc())
        if status:
            stmt = stmt.where(AccessRequest.status == status)
        return list(self.db.execute(stmt).scalars().all())

    def get_request(self, request_id: str) -> AccessRequest:
        request = self.db.get(AccessRequest, request_id)
        if request is None:
            raise NotFoundAppError("访问申请不存在")
        return request

    def build_ai_review(self, request_id: str) -> dict[str, str]:
        request = self.get_request(request_id)
        document = self.db.get(Document, request.document_id)
        applicant = self.db.get(User, request.user_id)
        if document is None or applicant is None:
            result = ReviewAgent(self.db).review(
                ReviewRequest(
                    review_type="document_access",
                    subject={
                        "reason": request.reason,
                        "business_purpose": request.business_purpose,
                        "expected_duration": request.expected_duration,
                        "applicant": None,
                    },
                    context={"document": None, "error": "申请关联的用户或文档不存在"},
                )
            )
        else:
            result = ReviewAgent(self.db).review(
                ReviewRequest(
                    review_type="document_access",
                    subject={
                        "reason": request.reason,
                        "business_purpose": request.business_purpose,
                        "expected_duration": request.expected_duration,
                        "applicant": {
                            "employee_no": applicant.employee_no,
                            "permission_level": applicant.permission_level,
                            "position": applicant.position,
                        },
                    },
                    context={
                        "document": {
                            "file_name": document.file_name,
                            "knowledge_space": document.knowledge_space,
                            "visibility_type": document.visibility_type,
                            "security_level": document.security_level,
                            "min_permission_level": document.min_permission_level,
                            "allowed_departments": document.allowed_departments,
                            "allowed_job_categories": document.allowed_job_categories,
                        }
                    },
                )
            )

        request.ai_suggestion = result.suggestion
        request.ai_risk_level = result.risk_level
        request.ai_reason = result.reason.strip()[:2000]
        self.db.commit()
        self.db.refresh(request)
        return {
            "suggestion": request.ai_suggestion or "review",
            "risk_level": request.ai_risk_level or "medium",
            "reason": request.ai_reason or "AI 未返回明确理由，建议管理员人工复核。",
        }

    def review_request(self, request_id: str, approve: bool, reviewer: AuthenticatedUser, review_comment: str | None = None) -> AccessRequest:
        request = self.get_request(request_id)
        if request.status != "pending":
            raise ValidationAppError("已审核的申请不能重复审核")

        document = self.db.get(Document, request.document_id)
        if document is None:
            raise NotFoundAppError("申请关联的文档不存在")

        request.status = "approved" if approve else "rejected"
        request.reviewed_by = reviewer.user_id
        request.review_comment = (review_comment or "").strip() or None
        request.reviewed_at = datetime.now(timezone.utc)

        if approve:
            self._create_grant(request.user_id, document.document_id, reviewer.user_id)

        self.db.commit()
        self.db.refresh(request)
        return request

    def get_request_context(self, request: AccessRequest) -> dict[str, object | None]:
        applicant = self.db.get(User, request.user_id)
        department = self.db.get(Department, applicant.department_id) if applicant and applicant.department_id else None
        document = self.db.get(Document, request.document_id)
        return {"applicant": applicant, "department": department, "document": document}

    def _has_valid_grant(self, document_id: str, user_id: str) -> bool:
        now = datetime.now(timezone.utc)
        grant = self.db.execute(
            select(DocumentAccessGrant).where(
                DocumentAccessGrant.user_id == user_id,
                DocumentAccessGrant.document_id == document_id,
                or_(DocumentAccessGrant.expire_at.is_(None), DocumentAccessGrant.expire_at > now),
            )
        ).scalar_one_or_none()
        return grant is not None

    def _create_grant(self, user_id: str, document_id: str, reviewer_id: str) -> DocumentAccessGrant:
        existed = self.db.execute(
            select(DocumentAccessGrant).where(
                DocumentAccessGrant.user_id == user_id,
                DocumentAccessGrant.document_id == document_id,
                or_(DocumentAccessGrant.expire_at.is_(None), DocumentAccessGrant.expire_at > datetime.now(timezone.utc)),
            )
        ).scalar_one_or_none()
        if existed is not None:
            return existed

        grant = DocumentAccessGrant(
            grant_id=str(uuid.uuid4()),
            user_id=user_id,
            document_id=document_id,
            granted_by=reviewer_id,
            expire_at=None,
        )
        self.db.add(grant)
        return grant

    def _active_public_ref(self, document: Document) -> PublicKnowledgeRef | None:
        return self.db.execute(
            select(PublicKnowledgeRef)
            .where(
                PublicKnowledgeRef.document_id == document.document_id,
                PublicKnowledgeRef.status == "active",
            )
            .order_by(PublicKnowledgeRef.created_at.desc())
        ).scalars().first()

    def _ask_deepseek_for_review(self, request: AccessRequest, applicant: User, document: Document) -> dict[str, str] | None:
        if not settings.deepseek_api_key:
            return None
        department = self.db.get(Department, applicant.department_id) if applicant.department_id else None
        prompt = {
            "task": "企业知识库文档访问申请辅助审核。你只提供建议，不能自动审批。",
            "output_schema": {"suggestion": "approve|reject|review", "risk_level": "low|medium|high", "reason": "中文理由，100-300字"},
            "applicant": {
                "employee_no": applicant.employee_no,
                "department": department.department_name if department else None,
                "permission_level": applicant.permission_level,
                "position": applicant.position,
            },
            "document": {
                "file_name": document.file_name,
                "knowledge_space": document.knowledge_space,
                "visibility_type": document.visibility_type,
                "security_level": document.security_level,
                "min_permission_level": document.min_permission_level,
                "allowed_departments": document.allowed_departments,
                "allowed_job_categories": document.allowed_job_categories,
            },
            "request": {
                "reason": request.reason,
                "business_purpose": request.business_purpose,
                "expected_duration": request.expected_duration,
            },
        }
        payload = {
            "model": settings.deepseek_model,
            "messages": [
                {"role": "system", "content": "你是企业知识访问风控助手。只输出 JSON，不要输出 Markdown。AI 只能辅助建议，最终由管理员人工审批。"},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            "stream": False,
            "temperature": 0.2,
        }
        headers = {"Authorization": f"Bearer {settings.deepseek_api_key}", "Content-Type": "application/json"}
        try:
            response = httpx.post(f"{settings.deepseek_base_url.rstrip('/')}/chat/completions", headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            return self._parse_ai_json(content)
        except Exception:
            self.db.rollback()
            return None

    def _parse_ai_json(self, content: str) -> dict[str, str] | None:
        text = content.strip()
        if not text:
            return None
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()
        try:
            data = json.loads(text)
        except Exception:
            return None
        if not isinstance(data, dict):
            return None
        return {
            "suggestion": str(data.get("suggestion") or "review"),
            "risk_level": str(data.get("risk_level") or "medium"),
            "reason": str(data.get("reason") or "建议管理员人工复核。"),
        }

    def _fallback_ai_review(self, request: AccessRequest, applicant: User, document: Document) -> dict[str, str]:
        reason_parts: list[str] = []
        risk_level = "low"
        suggestion = "approve"

        if len(request.reason.strip()) < 8 or len(request.business_purpose.strip()) < 8:
            suggestion = "review"
            risk_level = "medium"
            reason_parts.append("申请原因或业务用途较短，需要管理员确认真实业务场景。")

        user_level = int(applicant.permission_level or 1)
        min_level = int(document.min_permission_level or 1)
        if user_level < min_level:
            suggestion = "reject"
            risk_level = "high"
            reason_parts.append(f"申请人权限等级 L{user_level} 低于文档要求 L{min_level}。")

        security_level = (document.security_level or "internal").lower()
        if security_level in {"secret", "confidential", "restricted"}:
            if suggestion != "reject":
                suggestion = "review"
            risk_level = "high"
            reason_parts.append("文档安全等级较高，建议管理员重点核验必要性和使用范围。")

        allowed_departments = self._parse_list(document.allowed_departments)
        department = self.db.get(Department, applicant.department_id) if applicant.department_id else None
        if allowed_departments and (department.department_name if department else "") not in allowed_departments:
            if suggestion != "reject":
                suggestion = "review"
            risk_level = "medium" if risk_level == "low" else risk_level
            reason_parts.append("申请人所在部门不在文档配置的开放部门中。")

        if not reason_parts:
            reason_parts.append("申请信息完整，未发现明显权限等级或部门风险，可考虑通过，但仍需管理员人工确认。")

        return {"suggestion": suggestion, "risk_level": risk_level, "reason": " ".join(reason_parts)}

    def _normalize_suggestion(self, value: str | None) -> str:
        value = (value or "").lower().strip()
        return value if value in {"approve", "reject", "review"} else "review"

    def _normalize_risk_level(self, value: str | None) -> str:
        value = (value or "").lower().strip()
        return value if value in {"low", "medium", "high"} else "medium"

    def _parse_list(self, raw: str | None) -> set[str]:
        if not raw:
            return set()
        text = raw.strip()
        if not text:
            return set()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return {str(item).strip() for item in parsed if str(item).strip()}
        except Exception:
            pass
        return {item.strip() for item in text.replace("；", ",").replace(";", ",").split(",") if item.strip()}

    def _matches_job_category(self, allowed_jobs: set[str], user: AuthenticatedUser) -> bool:
        normalized = {item.lower() for item in allowed_jobs}
        if normalized.intersection({"all", "company", "public", "全公司", "全部", "所有人"}):
            return True
        candidates = {
            (user.department or "").lower(),
            (user.position or "").lower(),
            (user.employee_no or "").lower(),
        }
        candidates.update(role.lower() for role in user.roles)
        return bool(normalized.intersection(candidates))
