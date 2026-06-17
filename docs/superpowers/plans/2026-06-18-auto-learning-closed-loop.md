# Auto Learning Closed Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an organization-level automatic learning loop: collect knowledge gaps, generate AI draft knowledge, let admins review and edit, then publish approved knowledge through public knowledge references.

**Architecture:** Keep personal AI expansion as a personal knowledge feature. Add an organization-level learning workflow on top of existing low-confidence records, feedback, tasks, knowledge documents, and public publish review. AI can generate drafts, but only admins can approve and publish public references.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, Next.js, existing DeepSeek integration, existing `Document` / `DocumentChunk` / `PublicKnowledgeRef` model.

---

## File Structure

- Modify `app/models/core.py`: extend or connect existing `KnowledgeGap`-like data if present; otherwise keep gap model in the closest existing flywheel model file.
- Modify `app/schemas/flywheel.py`: add request/response schemas for gap list, draft generation, draft review.
- Modify `app/services/flywheel.py`: implement gap aggregation, duplicate grouping, draft generation entry point.
- Modify `app/services/knowledge_service.py`: keep personal AI expansion unchanged; add helper for creating generated draft documents in personal/admin space when needed.
- Modify `app/services/knowledge_publish.py`: reuse public publish request and `PublicKnowledgeRef`; do not mutate original documents into public.
- Modify `app/api/routes.py`: add admin endpoints for learning gaps, draft generation, draft approval/rejection.
- Modify `frontend/src/app/tasks/page.tsx`: turn automatic learning into a more readable “知识缺口工作台”.
- Modify `frontend/src/lib/display-labels.ts`: add Chinese labels for new task/gap/draft statuses.
- Create `alembic/versions/0016_learning_gap_drafts.py`: add missing draft fields/tables if current schema lacks them.
- Create `docs/自动学习闭环说明.md`: document demo flow and expected behavior.

---

## Task 1: Confirm Existing Gap Model And Add Draft Fields

**Files:**
- Inspect: `app/models/core.py`
- Inspect: `app/schemas/flywheel.py`
- Modify: `app/models/core.py`
- Modify: `app/schemas/flywheel.py`
- Create: `alembic/versions/0016_learning_gap_drafts.py`

- [ ] Step 1: Inspect existing gap-related models.

Run:

```powershell
rg -n "KnowledgeGap|gap|low_confidence|feedback|Learning" app
```

Expected: identify the current model/table used by `KnowledgeFlywheelService.create_gap`.

- [ ] Step 2: Add fields only if missing.

Required data shape:

```python
issue_type: str
query_text: str
normalized_question: str | None
user_id: str | None
confidence: float | None
evidence: str | None
status: str  # pending | drafted | approved | rejected | merged | ignored
cluster_key: str | None
hit_count: int
draft_document_id: str | None
ai_draft_content: str | None
pending_confirmations: str | None
admin_final_content: str | None
review_comment: str | None
reviewed_by: str | None
reviewed_at: datetime | None
```

- [ ] Step 3: Write migration.

Migration behavior:

```python
def upgrade() -> None:
    # Add nullable columns to existing knowledge gap table, or create a new
    # learning_gap_drafts table if the existing table is not appropriate.
```

Expected: migration is idempotent enough for the current local database.

- [ ] Step 4: Run migration.

Run:

```powershell
python -m alembic upgrade head
```

Expected: migration succeeds on PostgreSQL.

---

## Task 2: Normalize And Aggregate Knowledge Gaps

**Files:**
- Modify: `app/services/flywheel.py`
- Modify: `app/schemas/flywheel.py`
- Modify: `app/api/routes.py`

- [ ] Step 1: Add a normalizer.

Implementation intent:

```python
def normalize_gap_question(text: str) -> str:
    value = text.strip().lower()
    value = re.sub(r"\s+", "", value)
    value = re.sub(r"[？?。,.，!！]", "", value)
    return value[:120]
```

- [ ] Step 2: Update gap creation to aggregate similar questions.

Behavior:

```python
existing = find pending/drafted gap with same normalized_question
if existing:
    existing.hit_count += 1
    existing.evidence = append short evidence
else:
    create new gap with hit_count = 1
```

- [ ] Step 3: Add admin gap list endpoint.

Endpoint:

```text
GET /api/v1/admin/learning-gaps?status=pending
```

Response includes:

```python
gap_id
query_text
issue_type
confidence
hit_count
status
evidence
draft_document_id
created_at
updated_at
```

- [ ] Step 4: Keep personal AI expansion unchanged.

Rule: `/api/v1/knowledge/expand` remains user-triggered and writes to personal knowledge only.

---

## Task 3: Generate AI Draft Knowledge For A Gap

**Files:**
- Modify: `app/services/flywheel.py`
- Modify: `app/services/knowledge_service.py`
- Modify: `app/api/routes.py`
- Modify: `app/schemas/flywheel.py`

- [ ] Step 1: Add draft generation schema.

Request:

```python
class LearningGapDraftCreate(BaseModel):
    target_category: str
    allowed_job_categories: str
    business_purpose: str
```

Response:

```python
class LearningGapDraftRead(BaseModel):
    gap_id: str
    draft_document_id: str | None
    ai_draft_content: str
    pending_confirmations: str
    status: str
```

- [ ] Step 2: Generate draft with DeepSeek when available.

Prompt output must include:

```json
{
  "title": "VPN账号申请流程",
  "draft_content": "可编辑草稿正文",
  "pending_confirmations": ["真实工单入口", "审批人", "SLA时长"],
  "risk_note": "AI草稿需管理员确认后发布"
}
```

- [ ] Step 3: Add fallback when DeepSeek unavailable.

Fallback draft:

```markdown
# 待补充知识：{query}

## 问题背景
系统发现该问题在问答中未被充分回答。

## AI草稿
请管理员根据企业实际流程补充标准答案。

## 待确认事项
- 适用范围
- 负责人或审批人
- 官方入口或文档链接
- 注意事项
```

- [ ] Step 4: Store draft as personal/admin draft, not public.

Behavior:

```python
document.knowledge_space = "personal"
document.owner_user_id = admin_user.user_id
document.publish_status = "none"
document.visibility_type = "private"
```

---

## Task 4: Admin Review Draft And Publish Through Existing Public Ref

**Files:**
- Modify: `app/services/flywheel.py`
- Modify: `app/services/knowledge_publish.py`
- Modify: `app/api/routes.py`
- Modify: `app/schemas/flywheel.py`

- [ ] Step 1: Add draft review schema.

Request:

```python
class LearningGapDraftReview(BaseModel):
    approve: bool
    admin_final_content: str | None = None
    target_category: str | None = None
    allowed_job_categories: str | None = None
    review_comment: str | None = None
```

- [ ] Step 2: On approve, update draft document content.

Behavior:

```python
if admin_final_content:
    document.content_text = admin_final_content
    replace or append document chunk
```

- [ ] Step 3: Create a publish request and approve it through existing service.

Rules:

```python
KnowledgePublishService.create_request(...)
KnowledgePublishService.review_request(approve=True, reviewer=admin)
```

Expected: original draft document remains personal; approved public knowledge is represented by `PublicKnowledgeRef`.

- [ ] Step 4: On reject, keep draft private.

Behavior:

```python
gap.status = "rejected"
document.knowledge_space = "personal"
no PublicKnowledgeRef is created
```

---

## Task 5: Build Admin “知识缺口工作台”

**Files:**
- Modify: `frontend/src/app/tasks/page.tsx`
- Modify: `frontend/src/lib/display-labels.ts`

- [ ] Step 1: Replace raw task labels with Chinese labels.

Labels:

```ts
learning_gap: '知识缺口',
drafted: '已生成草稿',
merged: '已合并',
ignored: '暂不处理',
needs_confirmation: '需人工确认'
```

- [ ] Step 2: Add gap list area.

UI sections:

```text
知识缺口列表
状态筛选：待处理 / 已生成草稿 / 已发布 / 已拒绝 / 已忽略
字段：问题、类型、出现次数、置信度、证据、状态
```

- [ ] Step 3: Add “生成草稿” button for pending gaps.

Click behavior:

```text
POST /api/v1/admin/learning-gaps/{gap_id}/draft
```

- [ ] Step 4: Add draft editor.

Fields:

```text
AI草稿内容
待确认事项
管理员定稿内容
目标分类
可访问人员工作类别
审核意见
通过发布 / 拒绝
```

---

## Task 6: Documentation And Demo Script

**Files:**
- Create: `docs/自动学习闭环说明.md`
- Modify: `README.md` if needed

- [ ] Step 1: Write feature explanation.

Must explain:

```text
个人 AI 补充：用户手动触发，默认进入个人知识空间。
组织级自动学习：系统统计低置信度/失败问答，AI 生成草稿，管理员审核后发布为公有引用。
AI 不自动审批。
公有知识引用不复制、不篡改原始文档。
```

- [ ] Step 2: Write demo flow.

Demo:

```text
1. 普通用户提问系统答不好的问题。
2. 系统记录知识缺口。
3. 管理员进入自动学习页面。
4. 点击生成草稿。
5. 管理员修改定稿内容。
6. 点击通过发布。
7. 普通用户重新提问，系统能检索到审核后的公有知识。
```

---

## Verification Plan

### Backend Checks

- [ ] Run syntax check.

```powershell
python -m compileall app
```

Expected: no compile errors.

- [ ] Run migration.

```powershell
python -m alembic upgrade head
```

Expected: reaches latest migration without error.

- [ ] Verify personal AI expansion remains personal.

Scenario:

```text
E1001 asks a question -> clicks AI 扩充 -> generated document owner is E1001 -> knowledge_space is personal -> E1002 cannot search it.
```

- [ ] Verify organization learning gap creation.

Scenario:

```text
Ask a question with low confidence or unknown answer.
Check admin learning gap list.
Expected: pending gap exists, hit_count >= 1.
```

- [ ] Verify gap aggregation.

Scenario:

```text
Ask “VPN如何申请” and “怎么申请VPN”.
Expected: same normalized gap or same cluster, hit_count increases.
```

- [ ] Verify AI draft generation fallback.

Scenario:

```text
Temporarily remove DeepSeek API key.
POST draft endpoint.
Expected: fallback draft is generated and status becomes drafted.
```

- [ ] Verify admin approval.

Scenario:

```text
Admin edits final content and approves.
Expected:
document remains personal/private;
PublicKnowledgeRef active row exists;
gap status becomes approved;
normal user can search approved public knowledge.
```

- [ ] Verify admin rejection.

Scenario:

```text
Admin rejects draft.
Expected:
gap status becomes rejected;
document remains personal/private;
no active PublicKnowledgeRef is created.
```

### Frontend Checks

- [ ] Build frontend.

```powershell
cd frontend
npm run build
```

Expected: build succeeds.

- [ ] Manual UI check.

Pages:

```text
http://127.0.0.1:3000/tasks
http://127.0.0.1:3000/documents
http://127.0.0.1:3000/conversations
```

Expected:

```text
管理员 can see knowledge gap workbench.
普通用户 cannot see admin-only review controls.
Draft editor can save and submit review.
Published public ref appears as public knowledge, while original document still shows personal origin.
```

### Regression Checks

- [ ] Existing login and first-password-change still work.
- [ ] Existing document upload still defaults to personal.
- [ ] Existing document access request flow still works.
- [ ] Existing public publish review still works.
- [ ] Existing AI chat still streams and records conversation turns.
- [ ] Existing CSV/PDF preview still opens with auth token.

### Git Plan

- [ ] Commit after backend data model and service pass.

```powershell
git commit -m "feat: add learning gap draft backend"
```

- [ ] Commit after frontend workbench build passes.

```powershell
git commit -m "feat: add automatic learning workbench"
```

- [ ] Commit docs.

```powershell
git commit -m "docs: describe automatic learning closed loop"
```

