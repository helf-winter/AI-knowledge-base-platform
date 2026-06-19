# Dynamic Expert Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make generated expert-agent profiles actively control RAG scope, prompt identity, routing metadata, and frontend display.

**Architecture:** Use one configuration-driven execution path. Resolve an `ExpertAgentProfile` from explicit `agent_id` or auto recommendation, convert it to an execution context, pass scope filters into knowledge search, and include the expert identity in DeepSeek prompts and streaming metadata.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Next.js, Python unittest.

---

### Task 1: Backend tests for execution context

**Files:**
- Create: `tests/test_dynamic_expert_agent.py`

- [ ] Test explicit `agent_id` resolves an active profile.
- [ ] Test `knowledge_scope_json` with `document_id` filters out unrelated search results.
- [ ] Test DeepSeek message building includes expert name and domain.

### Task 2: Expert execution implementation

**Files:**
- Create: `app/services/expert_agent_runtime.py`
- Modify: `app/skills/knowledge_search.py`
- Modify: `app/agents/expert_agent.py`
- Modify: `app/services/deepseek.py`
- Modify: `app/services/knowledge_service.py`
- Modify: `app/api/routes.py`

- [ ] Add `ExpertAgentRuntime` to resolve explicit and recommended profiles.
- [ ] Add search scope filtering for document IDs, knowledge category, and keyword text.
- [ ] Add expert prompt context to DeepSeek message building.
- [ ] Return actual agent metadata and selected skills in chat stream end event.

### Task 3: Frontend metadata display

**Files:**
- Modify: `frontend/src/components/layout/floating-assistant.tsx`

- [ ] Read actual agent metadata from the stream end event.
- [ ] Display “使用专家：xxx” and reason under the answer metadata.
- [ ] Keep current behavior when no expert is selected.

### Task 4: Verification

**Files:**
- Verify all changed files.

- [ ] Run `python -m unittest tests.test_dynamic_expert_agent -v`.
- [ ] Run `python -m unittest discover -s tests -p "test_*.py" -v`.
- [ ] Run `python -m compileall app`.
- [ ] Run `npm run build` in `frontend`.

