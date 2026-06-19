# Manual Knowledge Authoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a page-level entry for employees and admins to manually write Markdown knowledge that is saved as personal knowledge and can later enter the existing public publish review flow.

**Architecture:** Reuse the existing `documents` and `document_chunks` model. Manual knowledge is stored as a generated `.md` document with `knowledge_space="personal"`, `owner_user_id` set to the current user, one or more chunks for search, and metadata with `source_type="manual"`.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Next.js App Router, existing UI components, unittest.

---

### Task 1: Backend Manual Knowledge API

**Files:**
- Modify: `app/schemas/knowledge.py`
- Modify: `app/services/knowledge_service.py`
- Modify: `app/api/routes.py`
- Test: `tests/test_manual_knowledge_authoring.py`

- [ ] **Step 1: Write failing backend tests**

Add tests proving manual knowledge creates a private Markdown document owned by the current user, creates chunks, creates metadata, rejects blank content, and remains compatible with publish request creation.

- [ ] **Step 2: Run focused test and verify RED**

Run: `python -m unittest tests.test_manual_knowledge_authoring -v`
Expected: FAIL because `ManualKnowledgeCreate` and `KnowledgeService.create_manual_knowledge` do not exist yet.

- [ ] **Step 3: Implement schemas, service method, and route**

Add `ManualKnowledgeCreate` with title, content, category, business_purpose, allowed_job_categories, and tags. Add `KnowledgeService.create_manual_knowledge(...)` that creates a generated `.md` personal document, chunks it, creates embeddings and metadata. Add `POST /api/v1/documents/manual`.

- [ ] **Step 4: Run focused test and verify GREEN**

Run: `python -m unittest tests.test_manual_knowledge_authoring -v`
Expected: PASS.

### Task 2: Knowledge Page Authoring UI

**Files:**
- Modify: `frontend/src/app/documents/page.tsx`

- [ ] **Step 1: Add typed API helper**

Add a `createManualKnowledge` helper that posts to `/api/v1/documents/manual`.

- [ ] **Step 2: Add authoring card**

Add a “手动记录知识” card beside upload, with title, category, applicable job categories, business purpose, tags, and Markdown body.

- [ ] **Step 3: Save behavior**

On save, call the helper, reload document list, and navigate to the created document detail page. Keep the document personal by default.

### Task 3: Verification

**Files:**
- Existing project commands only.

- [ ] **Step 1: Run backend tests**

Run: `python -m unittest discover -s tests -p 'test_*.py' -v`
Expected: PASS.

- [ ] **Step 2: Compile backend**

Run: `python -m compileall app`
Expected: PASS.

- [ ] **Step 3: Build frontend**

Run: `npm run build` in `frontend`
Expected: PASS.

- [ ] **Step 4: Inspect git diff**

Run: `git diff --check`, `git diff --stat`, and `git status --short`.
Expected: no syntax issues; only intended files changed.
