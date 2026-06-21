# Publish AI Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add AI-assisted recommendations to public knowledge publish review without allowing AI to approve requests.

**Architecture:** Persist three AI review fields on `KnowledgePublishRequest`, generate them through the existing `ReviewAgent`, expose an admin-only endpoint, and render the result next to the manual approval controls. DeepSeek failure continues through the existing rule fallback.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, Next.js, TypeScript, pytest.

---

### Task 1: Persist and generate publish review advice

**Files:** `tests/test_publish_ai_review.py`, `app/models/document.py`, `app/schemas/knowledge.py`, `app/services/knowledge_publish.py`, `alembic/versions/0023_publish_request_ai_review.py`

- [ ] Run the new test and confirm it fails because `build_ai_review` and the response fields do not exist.
- [ ] Add nullable AI suggestion, risk and reason columns plus an Alembic migration.
- [ ] Build a `knowledge_publish` review request from the application and document context, persist the normalized result, and keep status unchanged.
- [ ] Run the focused test and confirm it passes.

### Task 2: Add protected API and administrator UI

**Files:** `app/api/routes.py`, `frontend/src/app/admin/page.tsx`, `tests/test_publish_ai_review.py`

- [ ] Add an admin/reviewer-only POST endpoint and audit event.
- [ ] Add the authenticated frontend request, loading state, action button and result card.
- [ ] Keep manual approve/reject as the only status-changing actions.
- [ ] Run the focused test and frontend build.

### Task 3: Verify the complete behavior

**Files:** all files changed above

- [ ] Run the full backend test suite.
- [ ] Run the production frontend build.
- [ ] Run Alembic upgrade and verify the endpoint in the running application.
