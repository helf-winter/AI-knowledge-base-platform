# Unified Review Agent And Answer Quality Signals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a unified `ReviewAgent` service that provides structured review suggestions for answer quality, document access, public knowledge publishing, and automatic-learning drafts, while ensuring humans remain the final approvers.

**Architecture:** Introduce a reusable review layer with one output schema: `suggestion`, `risk_level`, `reason`, `missing_information`, `evidence`, and `next_action`. Existing business flows keep their own final state transitions, but delegate risk analysis and recommendation generation to `ReviewAgent`. Answer-quality signals then use this agent to decide when to create reviewable `KnowledgeGap` records.

**Tech Stack:** FastAPI, SQLAlchemy, existing DeepSeek config, existing `KnowledgeGap`, `AccessRequest`, `KnowledgePublishRequest`, `PublicKnowledgeRef`, existing automatic-learning workbench, Next.js display labels.

---

## Current State

The system already has several separate review-like behaviors:

- `DocumentAccessService.build_ai_review()` generates AI suggestions for document access requests.
- `KnowledgePublishService.review_request()` lets admins approve or reject personal knowledge publishing.
- `KnowledgeFlywheelService.generate_gap_draft()` generates AI/fallback drafts for knowledge gaps.
- `chat_stream()` detects fallback-to-general answers with `should_fallback`.
- `KnowledgeService.record_feedback()` stores user feedback, but does not create learning gaps yet.
- `KnowledgeFlywheelService.create_gap()` aggregates repeated knowledge gaps.

The missing abstraction is:

- no unified review result model
- no single `ReviewAgent.review(...)` entry point
- answer-quality review is not represented as a formal review type
- negative feedback and fallback answers are not consistently converted into knowledge gaps
- existing access review and future publish/draft review logic are scattered

---

## Review Agent Contract

All review scenarios should return this shape:

```python
class ReviewResult(BaseModel):
    review_type: str
    suggestion: str  # approve | reject | review
    risk_level: str  # low | medium | high
    reason: str
    missing_information: list[str] = []
    evidence: list[str] = []
    next_action: str | None = None
```

Supported review types:

```python
answer_quality
document_access
knowledge_publish
learning_gap_draft
```

Rule:

```text
ReviewAgent only gives advice. It must never directly approve access, publish knowledge, delete documents, or mark knowledge as public.
```

---

## File Structure

- Create `app/agents/review_agent.py`: unified review agent with DeepSeek and fallback rule-based reviewers.
- Create or modify `app/schemas/review.py`: shared review request/response schemas.
- Modify `app/services/access_control.py`: make `build_ai_review()` delegate to `ReviewAgent` for `document_access`.
- Modify `app/services/flywheel.py`: use `ReviewAgent` for `answer_quality` and `learning_gap_draft` where appropriate.
- Modify `app/services/knowledge_service.py`: convert negative feedback into reviewable knowledge gaps through `ReviewAgent`.
- Modify `app/api/routes.py`: create fallback answer quality reviews inside `chat_stream`; pass `user_id` into feedback recording.
- Modify `frontend/src/lib/display-labels.ts`: add Chinese labels for new review and gap types.
- Optional modify `frontend/src/app/conversations/page.tsx`: add visible user feedback buttons if missing.
- Optional modify `frontend/src/app/tasks/page.tsx`: display review evidence/reason if available in gap evidence.
- Create or update `docs/自动学习闭环说明.md`: describe unified review agent.

---

## Task 1: Add Shared Review Schemas

**Files:**
- Create: `app/schemas/review.py`

- [ ] Step 1: Create `ReviewRequest` and `ReviewResult`.

Create file:

```python
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    review_type: str = Field(pattern="^(answer_quality|document_access|knowledge_publish|learning_gap_draft)$")
    subject: dict[str, Any]
    context: dict[str, Any] = Field(default_factory=dict)


class ReviewResult(BaseModel):
    review_type: str
    suggestion: str = Field(pattern="^(approve|reject|review)$")
    risk_level: str = Field(pattern="^(low|medium|high)$")
    reason: str
    missing_information: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    next_action: str | None = None
```

- [ ] Step 2: Run compile check.

Run:

```powershell
python -m compileall app
```

Expected:

```text
Compiling 'app\\schemas\\review.py'...
```

---

## Task 2: Implement Unified ReviewAgent

**Files:**
- Create: `app/agents/review_agent.py`

- [ ] Step 1: Create agent skeleton.

Create:

```python
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
```

- [ ] Step 2: Add DeepSeek review method.

Add:

```python
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
                missing_information=[str(item) for item in data.get("missing_information", []) if str(item).strip()],
                evidence=[str(item) for item in data.get("evidence", []) if str(item).strip()],
                next_action=str(data.get("next_action")).strip() if data.get("next_action") else None,
            )
        except Exception:
            return None
```

- [ ] Step 3: Add parser and normalizers.

Add:

```python
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
```

- [ ] Step 4: Add fallback dispatcher.

Add:

```python
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
```

- [ ] Step 5: Add answer quality fallback.

Add:

```python
    def _fallback_answer_quality(self, payload: ReviewRequest) -> ReviewResult:
        subject = payload.subject
        confidence = float(subject.get("confidence") or 0.0)
        mode = str(subject.get("mode") or "")
        has_sources = bool(subject.get("has_sources"))
        user_feedback = subject.get("user_feedback") or {}
        rating = int(user_feedback.get("rating") or 0)
        is_helpful = user_feedback.get("is_helpful")

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
```

- [ ] Step 6: Add simpler fallbacks for other review types.

Add:

```python
    def _fallback_document_access(self, payload: ReviewRequest) -> ReviewResult:
        subject = payload.subject
        reason = str(subject.get("reason") or "")
        purpose = str(subject.get("business_purpose") or "")
        security_level = str(payload.context.get("document", {}).get("security_level") or "internal")
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
            missing_information=[str(item) for item in confirmations if str(item).strip()],
            evidence=["自动学习生成草稿"],
            next_action="管理员确认后发布",
        )
```

- [ ] Step 7: Run compile check.

Run:

```powershell
python -m compileall app
```

Expected: no compile errors.

---

## Task 3: Delegate Document Access AI Review To ReviewAgent

**Files:**
- Modify: `app/services/access_control.py`

- [ ] Step 1: Import ReviewAgent and ReviewRequest.

Add:

```python
from app.agents.review_agent import ReviewAgent
from app.schemas.review import ReviewRequest
```

- [ ] Step 2: Replace the inside of `build_ai_review()`.

Keep request lookup logic, then build payload:

```python
result = ReviewAgent(self.db).review(
    ReviewRequest(
        review_type="document_access",
        subject={
            "reason": request.reason,
            "business_purpose": request.business_purpose,
            "expected_duration": request.expected_duration,
            "applicant": {
                "employee_no": applicant.employee_no if applicant else None,
                "permission_level": applicant.permission_level if applicant else None,
                "position": applicant.position if applicant else None,
            },
        },
        context={
            "document": {
                "file_name": document.file_name if document else None,
                "knowledge_space": document.knowledge_space if document else None,
                "visibility_type": document.visibility_type if document else None,
                "security_level": document.security_level if document else None,
                "min_permission_level": document.min_permission_level if document else None,
                "allowed_departments": document.allowed_departments if document else None,
                "allowed_job_categories": document.allowed_job_categories if document else None,
            }
        },
    )
)
```

Then assign:

```python
request.ai_suggestion = result.suggestion
request.ai_risk_level = result.risk_level
request.ai_reason = result.reason[:2000]
```

- [ ] Step 3: Keep old private helper methods for now or delete only after tests pass.

Reason: reduce risk. If deleting old `_ask_deepseek_for_review()` and `_fallback_ai_review()` creates hidden coupling, do that in a later cleanup commit.

- [ ] Step 4: Verify access review still works.

Run a temporary script or use API:

```text
POST /api/v1/admin/access-requests/{request_id}/ai-review
```

Expected:

```json
{
  "suggestion": "approve|reject|review",
  "risk_level": "low|medium|high",
  "reason": "..."
}
```

---

## Task 4: Use ReviewAgent For Answer Quality Signals

**Files:**
- Modify: `app/api/routes.py`
- Modify: `app/services/knowledge_service.py`
- Modify: `app/services/flywheel.py`

- [ ] Step 1: In `chat_stream`, lower fallback confidence.

Replace:

```python
confidence = 0.75 if collected.strip() else 0.0
```

With:

```python
confidence = 0.25 if should_fallback else (0.75 if collected.strip() else 0.0)
```

- [ ] Step 2: In `chat_stream`, create answer-quality review payload after saving the turn.

Use:

```python
turn = ConversationService(db).create_turn(...)
```

Then:

```python
if should_fallback:
    review = ReviewAgent(db).review(
        ReviewRequest(
            review_type="answer_quality",
            subject={
                "query": payload.query,
                "answer": collected.strip(),
                "confidence": confidence,
                "mode": mode,
                "has_sources": bool(source_documents),
            },
            context={"trace_id": trace_id, "session_id": session_id},
        )
    )
    if review.suggestion == "review":
        service.flywheel.create_gap(
            KnowledgeGapCreate(
                query_text=payload.query,
                session_id=session_id,
                user_id=user.user_id,
                answer_id=turn.turn_id,
                issue_type="fallback_to_general_answer",
                confidence=confidence,
                evidence=json.dumps(review.model_dump(), ensure_ascii=False),
            )
        )
```

- [ ] Step 3: In `KnowledgeService.record_feedback()`, call ReviewAgent for negative feedback.

After creating `Feedback`, if `(not is_helpful) or rating <= 2`, find `ConversationTurn` and call:

```python
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
```

If `review.suggestion == "review"`, create gap:

```python
self.flywheel.create_gap(
    KnowledgeGapCreate(
        query_text=turn.query_text,
        session_id=turn.session_id,
        user_id=user_id or turn.user_id,
        answer_id=turn.turn_id,
        issue_type=issue_type or "negative_user_feedback",
        confidence=min(float(turn.confidence or 0.0), 0.3),
        evidence=json.dumps(review.model_dump(), ensure_ascii=False),
    )
)
```

- [ ] Step 4: Extend `auto_extract_gaps_from_turns()` for empty sources.

Use:

```python
refs = getattr(turn, "source_refs_json", None) or "[]"
has_sources = refs.strip() not in {"", "[]", "null"}
if confidence >= min_confidence and has_sources:
    continue
issue_type = "low_confidence_answer" if confidence < min_confidence else "answer_without_sources"
```

Then create a review:

```python
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
        context={"session_id": turn.session_id, "answer_id": turn.turn_id},
    )
)
```

Use `json.dumps(review.model_dump(), ensure_ascii=False)` as gap evidence.

---

## Task 5: Use ReviewAgent For Learning Gap Draft Review Suggestions

**Files:**
- Modify: `app/services/flywheel.py`

- [ ] Step 1: In `generate_gap_draft()`, after draft creation, call `ReviewAgent`.

Add:

```python
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
```

- [ ] Step 2: Store review result in `gap.evidence`.

Append:

```python
gap.evidence = self._append_evidence(gap.evidence, json.dumps({"draft_review": review.model_dump()}, ensure_ascii=False))
```

Expected: admin workbench can show why the draft needs human confirmation.

---

## Task 6: Add Display Labels For Unified Review Signals

**Files:**
- Modify: `frontend/src/lib/display-labels.ts`

- [ ] Step 1: Add labels.

Add:

```ts
answer_quality: '回答质量审核',
document_access: '文档访问审核',
knowledge_publish: '知识发布审核',
learning_gap_draft: '知识草稿审核',
fallback_to_general_answer: '已切换通用回答',
negative_user_feedback: '用户反馈不佳',
incomplete_answer: '回答不完整',
answer_without_sources: '回答缺少依据',
```

- [ ] Step 2: Build frontend.

Run:

```powershell
cd frontend
npm run build
```

Expected: build succeeds.

---

## Task 7: Optional Feedback UI Polish

**Files:**
- Inspect: `frontend/src/app/conversations/page.tsx`
- Optional Modify: `frontend/src/app/conversations/page.tsx`

- [ ] Step 1: Check existing feedback controls.

Run:

```powershell
rg -n "feedback|有帮助|没帮助|is_helpful|rating" frontend/src/app frontend/src/components
```

Expected:

```text
If controls exist, verify they submit session_id and answer_id.
If controls do not exist, add minimal feedback buttons under each answer.
```

- [ ] Step 2: If missing, add minimal buttons.

Use:

```tsx
<Button onClick={() => submitFeedback(turn, true, 5, undefined)}>有帮助</Button>
<Button onClick={() => submitFeedback(turn, false, 1, 'incomplete_answer')}>没解决</Button>
```

Payload:

```ts
{
  session_id: turn.session_id,
  answer_id: turn.turn_id,
  rating,
  is_helpful,
  issue_type,
  comment: issue_type === 'incomplete_answer' ? '用户认为回答不完整' : undefined,
}
```

---

## Verification Plan

- [ ] Backend compile.

```powershell
python -m compileall app
```

Expected: no compile errors.

- [ ] Migration check.

```powershell
python -m alembic upgrade head
```

Expected: no migration errors.

- [ ] ReviewAgent fallback test.

Temporary script:

```python
result = ReviewAgent(db).review(
    ReviewRequest(
        review_type="answer_quality",
        subject={"query": "VPN怎么申请", "answer": "通用回答", "confidence": 0.25, "mode": "auto_general", "has_sources": False},
        context={},
    )
)
assert result.suggestion == "review"
assert result.risk_level in {"medium", "high"}
```

- [ ] Fallback answer creates gap.

Scenario:

```text
Ask a question that has no knowledge-base answer.
System switches to general answer.
Expected: KnowledgeGap exists with issue_type=fallback_to_general_answer and evidence contains ReviewResult JSON.
```

- [ ] Negative feedback creates gap.

Scenario:

```text
Submit feedback is_helpful=false, rating=1.
Expected: KnowledgeGap exists with issue_type=incomplete_answer or negative_user_feedback.
```

- [ ] Positive feedback does not create gap.

Scenario:

```text
Submit feedback is_helpful=true, rating=5.
Expected: no KnowledgeGap is created.
```

- [ ] Access request AI review still works.

Scenario:

```text
Admin triggers AI review for an access request.
Expected: response still contains suggestion, risk_level, reason.
```

- [ ] Automatic learning scan creates source-less gap.

Scenario:

```text
ConversationTurn has confidence=0.75 and source_refs_json=[].
Run auto learning.
Expected: KnowledgeGap.issue_type == answer_without_sources.
```

- [ ] Admin workbench still works.

Scenario:

```text
Open /tasks as admin.
Expected: gaps show readable Chinese issue labels and can still generate/review drafts.
```

---

## Git Plan

- [ ] Commit unified ReviewAgent.

```powershell
git add app/agents/review_agent.py app/schemas/review.py app/services/access_control.py
git commit -m "feat: add unified review agent"
```

- [ ] Commit answer-quality signal integration.

```powershell
git add app/api/routes.py app/services/knowledge_service.py app/services/flywheel.py frontend/src/lib/display-labels.ts
git commit -m "feat: connect answer quality reviews to learning gaps"
```

- [ ] Commit optional feedback UI.

```powershell
git add frontend/src/app/conversations/page.tsx
git commit -m "feat: add answer feedback controls"
```

