# Large File Background Parsing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Use PostgreSQL as the final task state store, Redis/Celery as the background queue, and a worker to parse large uploaded documents while the frontend shows status and retry/continue actions.

**Architecture:** The upload API saves the original file, creates a `TaskRecord`, and dispatches a Celery job through Redis. The Celery worker opens its own database session, parses the document, writes chunks and embeddings, and updates task/document status in PostgreSQL. The frontend polls the existing task API for the selected document and lets users retry failed or stalled parsing tasks.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, Redis, Celery, Next.js.

---

### Task 1: Backend Task Model And Queue Dispatch

**Files:**
- Modify: `app/models/core.py`
- Modify: `app/schemas/task.py`
- Modify: `app/services/task_service.py`
- Modify: `app/services/knowledge_service.py`
- Modify: `app/tasks/jobs.py`
- Modify: `app/api/routes.py`
- Create: `alembic/versions/0020_task_progress_fields.py`
- Test: `tests/test_large_file_background_parsing.py`

- [ ] Add task progress fields: `stage`, `progress_current`, `progress_total`, `detail`.
- [ ] Add service helpers to mark queued/running/progress/succeeded/failed.
- [ ] Split document creation from parsing, so upload can return before parsing.
- [ ] Dispatch Celery job for documents above the configured threshold.
- [ ] Implement Celery `parse_document_task(document_id, task_id)`.
- [ ] Add retry endpoint that re-queues parse tasks for failed/stalled documents.

### Task 2: Frontend Status And Retry

**Files:**
- Modify: `frontend/src/app/documents/page.tsx`
- Modify: `frontend/src/lib/display-labels.ts`

- [ ] Extend task type with progress fields.
- [ ] Fetch tasks for the selected document.
- [ ] Poll while the selected document is queued/running/processing.
- [ ] Show stage, progress, and failure reason in the document summary card.
- [ ] Add retry/continue button for failed or stalled parse tasks.

### Task 3: Verification

**Commands:**
- `conda run -n knowledge-base python -m alembic upgrade head`
- `conda run -n knowledge-base python -m unittest discover -s tests -p "test_*.py" -v`
- `conda run -n knowledge-base python -m compileall app scripts`
- `npm run build` in `frontend`

**Manual checks:**
- Upload a small file: it may parse immediately.
- Upload a file above the large-file threshold: API returns quickly with queued/processing status.
- Start worker: `conda run -n knowledge-base celery -A app.worker.celery_app worker --pool=solo --loglevel=info`
- Confirm the frontend shows parsing stage/progress and can retry failed tasks.
