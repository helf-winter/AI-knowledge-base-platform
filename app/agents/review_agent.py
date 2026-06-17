from __future__ import annotations

import json

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.schemas.review import ReviewRequest, ReviewResult

settings = get_settings()


class ReviewAgent:
    def __init__(self, db: Session) -> None:
        self.db = db

    def review(self, payload: ReviewRequest) -> ReviewResult:
        result = self._ask_deepseek(payload)
        if result is None:
            result = self._fallback_review(payload)
        return result

    def _ask_deepseek(self, payload: ReviewRequest) -> ReviewResult | None:
        if not settings.deepseek_api_key:
            return None
        prompt = {
            "task": "你是企业知识管理平台的统一审核助手。只提供建议，不能自动审批。",
            "review_type": payload.review_type,
            "output_schema": {
                "suggestion": "approve|reject|review",
                "risk_level": "low|medium|high",
                "reason": "中文理由",
                "missing_information": ["缺失信息"],
                "evidence": ["证据"],
                "next_action": "建议下一步",
            },
            "subject": payload.subject,
            "context": payload.context,
        }
        request_payload = {
            "model": settings.deepseek_model,
            "messages": [
                {"role": "system", "content": "只输出 JSON。你只能给审核建议，最终审批必须由管理员完成。"},
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
            data = self._parse_json(content)
            if data is None:
                return None
            return ReviewResult(
                review_type=payload.review_type,
                suggestion=self._normalize_suggestion(data.get("suggestion")),
                risk_level=self._normalize_risk(data.get("risk_level")),
                reason=str(data.get("reason") or "AI 未返回明确理由，建议人工复核。"),
                missing_information=[str(item) for item in data.get("missing_information", []) if str(item).strip()] if isinstance(data.get("missing_information", []), list) else [],
                evidence=[str(item) for item in data.get("evidence", []) if str(item).strip()] if isinstance(data.get("evidence", []), list) else [],
                next_action=str(data.get("next_action")).strip() if data.get("next_action") else None,
            )
        except Exception:
            return None

    def _parse_json(self, content: str) -> dict[str, object] | None:
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

    def _normalize_suggestion(self, value: object) -> str:
        text = str(value or "").lower().strip()
        return text if text in {"approve", "reject", "review"} else "review"

    def _normalize_risk(self, value: object) -> str:
        text = str(value or "").lower().strip()
        return text if text in {"low", "medium", "high"} else "medium"

    def _fallback_review(self, payload: ReviewRequest) -> ReviewResult:
        if payload.review_type == "answer_quality":
            return self._fallback_answer_quality(payload)
        if payload.review_type == "document_access":
            return self._fallback_document_access(payload)
        if payload.review_type == "knowledge_publish":
            return self._fallback_knowledge_publish(payload)
        if payload.review_type == "learning_gap_draft":
            return self._fallback_learning_gap_draft(payload)
        return ReviewResult(
            review_type=payload.review_type,
            suggestion="review",
            risk_level="medium",
            reason="未识别的审核类型，建议管理员人工复核。",
            next_action="人工复核",
        )

    def _fallback_answer_quality(self, payload: ReviewRequest) -> ReviewResult:
        subject = payload.subject
        confidence = float(subject.get("confidence") or 0.0)
        mode = str(subject.get("mode") or "")
        has_sources = bool(subject.get("has_sources"))
        user_feedback = subject.get("user_feedback") or {}
        rating = int(user_feedback.get("rating") or 0) if isinstance(user_feedback, dict) else 0
        is_helpful = user_feedback.get("is_helpful") if isinstance(user_feedback, dict) else None

        evidence: list[str] = []
        missing: list[str] = []
        risk = "low"
        suggestion = "approve"
        reason_parts: list[str] = []

        if mode == "auto_general":
            suggestion = "review"
            risk = "medium"
            evidence.append("知识库回答不足，系统切换到通用回答")
            missing.append("缺少可引用的企业知识")
            reason_parts.append("回答依赖通用模型兜底，说明知识库覆盖不足。")

        if confidence < 0.45:
            suggestion = "review"
            risk = "medium"
            evidence.append(f"回答置信度较低：{confidence:.2f}")
            reason_parts.append("检索置信度低，可能存在知识缺口。")

        if not has_sources:
            suggestion = "review"
            risk = "medium"
            evidence.append("回答缺少来源依据")
            missing.append("可追溯知识来源")
            reason_parts.append("回答没有可追溯来源，不适合作为可靠企业知识直接复用。")

        if is_helpful is False or rating in {1, 2}:
            suggestion = "review"
            risk = "high" if rating == 1 else "medium"
            evidence.append("用户反馈回答未解决问题")
            reason_parts.append("用户负面反馈证明该回答质量不足。")

        if not reason_parts:
            reason_parts.append("未发现明显质量风险。")

        return ReviewResult(
            review_type="answer_quality",
            suggestion=suggestion,
            risk_level=risk,
            reason=" ".join(reason_parts),
            missing_information=missing,
            evidence=evidence,
            next_action="创建知识缺口并进入自动学习" if suggestion == "review" else "无需处理",
        )

    def _fallback_document_access(self, payload: ReviewRequest) -> ReviewResult:
        subject = payload.subject
        reason = str(subject.get("reason") or "")
        purpose = str(subject.get("business_purpose") or "")
        document = payload.context.get("document", {})
        security_level = str(document.get("security_level") or "internal") if isinstance(document, dict) else "internal"
        if len(reason.strip()) < 8 or len(purpose.strip()) < 8:
            return ReviewResult(
                review_type="document_access",
                suggestion="review",
                risk_level="medium",
                reason="申请原因或业务用途较短，建议管理员确认真实业务场景。",
                missing_information=["详细业务用途"],
                evidence=["申请信息不完整"],
                next_action="补充申请原因后复核",
            )
        if security_level in {"secret", "confidential", "restricted"}:
            return ReviewResult(
                review_type="document_access",
                suggestion="review",
                risk_level="high",
                reason="文档安全等级较高，需要管理员重点确认必要性。",
                evidence=[f"security_level={security_level}"],
                next_action="人工复核访问必要性",
            )
        return ReviewResult(
            review_type="document_access",
            suggestion="approve",
            risk_level="low",
            reason="申请信息完整，未发现明显权限风险。",
            evidence=["申请原因和业务用途完整"],
            next_action="管理员确认后可通过",
        )

    def _fallback_knowledge_publish(self, payload: ReviewRequest) -> ReviewResult:
        subject = payload.subject
        missing = []
        for key, label in [("target_category", "目标分类"), ("allowed_job_categories", "可访问人员工作类别"), ("business_purpose", "业务用途")]:
            if not str(subject.get(key) or "").strip():
                missing.append(label)
        if missing:
            return ReviewResult(
                review_type="knowledge_publish",
                suggestion="review",
                risk_level="medium",
                reason="发布申请缺少必要信息，不能直接进入公有知识库。",
                missing_information=missing,
                next_action="补充发布范围和用途",
            )
        return ReviewResult(
            review_type="knowledge_publish",
            suggestion="review",
            risk_level="medium",
            reason="公有知识发布需要管理员确认准确性、适用范围和安全边界。",
            evidence=["个人知识提交公有发布"],
            next_action="管理员人工审核后决定是否发布",
        )

    def _fallback_learning_gap_draft(self, payload: ReviewRequest) -> ReviewResult:
        subject = payload.subject
        content = str(subject.get("draft_content") or "")
        confirmations = subject.get("pending_confirmations") or []
        if len(content.strip()) < 50:
            return ReviewResult(
                review_type="learning_gap_draft",
                suggestion="review",
                risk_level="medium",
                reason="草稿内容较短，需要管理员补充事实依据和标准流程。",
                missing_information=["标准答案正文", "事实依据"],
                next_action="补充定稿内容后再发布",
            )
        return ReviewResult(
            review_type="learning_gap_draft",
            suggestion="review",
            risk_level="medium",
            reason="AI 草稿可作为编辑起点，但仍需管理员确认待确认事项。",
            missing_information=[str(item) for item in confirmations if str(item).strip()] if isinstance(confirmations, list) else [],
            evidence=["自动学习生成草稿"],
            next_action="管理员确认后发布",
        )
