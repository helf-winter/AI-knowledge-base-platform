# Role-Adaptive Dashboard And Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove employee dashboard gaps, hide the admin group label for employees, and restore feedback submission for current conversation turns.

**Architecture:** Keep one role-aware frontend and change only responsive grid classes and conditional labels. Preserve the feedback table data shape, remove obsolete database foreign keys, and enforce current-turn ownership in the service layer.

**Tech Stack:** Next.js 15, React 18, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, Python unittest.

---

### Task 1: Add failing role-layout regression checks

**Files:**
- Modify: `tests/test_admin_navigation_visibility.py`

- [ ] Assert that the dashboard summary grid uses an employee two-column class and an admin four-column class.
- [ ] Assert that the recent-answer section spans the full row for employees.
- [ ] Assert that the “管理入口” heading is conditional on `isAdminUser`.
- [ ] Run `python -m unittest discover -s tests -p "test_*.py" -v` and confirm the new assertions fail.

### Task 2: Implement role-adaptive layout

**Files:**
- Modify: `frontend/src/app/page.tsx`
- Modify: `frontend/src/components/layout/sidebar-shell.tsx`

- [ ] Build the summary and content grid class names from `isAdminUser`.
- [ ] Render the management group heading only for administrators and reviewers.
- [ ] Run the role-layout tests and confirm they pass.

### Task 3: Add failing feedback service tests

**Files:**
- Create: `tests/test_feedback_service.py`

- [ ] Test that a user can record feedback for their own `ConversationTurn`.
- [ ] Test that a missing turn raises `ValidationAppError` with a Chinese message.
- [ ] Test that a different user’s turn raises `PermissionAppError`.
- [ ] Run `python -m unittest tests.test_feedback_service -v` and confirm failures occur before implementation.

### Task 4: Repair feedback persistence and error handling

**Files:**
- Create: `alembic/versions/0017_fix_feedback_conversation_links.py`
- Modify: `app/services/knowledge_service.py`
- Modify: `app/api/routes.py`
- Modify: `frontend/src/app/conversations/page.tsx`

- [ ] Add migration `0017` after `0016_learning_gap_drafts` that drops `feedbacks_answer_id_fkey` and `feedbacks_session_id_fkey` when present.
- [ ] Resolve the current `ConversationTurn` before creating `Feedback`, enforce ownership, and then commit.
- [ ] Wrap the feedback route with the existing `_handle_app_error` boundary.
- [ ] Convert network failures to “无法连接后端服务，请确认后端已启动” in the frontend.
- [ ] Run feedback tests and confirm all pass.

### Task 5: Verify the complete change

**Files:**
- Verify all modified files above.

- [ ] Run `python -m alembic upgrade head` and inspect feedback foreign keys.
- [ ] Run `python -m compileall app`.
- [ ] Run `python -m unittest discover -s tests -p "test_*.py" -v`.
- [ ] Run `npm run build` in `frontend`.
- [ ] Inspect `git diff --check` and confirm no unrelated files were changed.

