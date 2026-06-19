from __future__ import annotations

from app.core.database import SessionLocal
from app.models.document import Document
from app.services.knowledge_service import KnowledgeService
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.jobs.noop")
def noop_task(payload: dict) -> dict:
    return {"ok": True, "payload": payload}


@celery_app.task(name="app.tasks.jobs.parse_document")
def parse_document_task(document_id: str, task_id: str) -> dict:
    db = SessionLocal()
    try:
        document = KnowledgeService(db).run_parse_document_task(document_id, task_id)
        return {"ok": True, "document_id": document.document_id, "parse_status": document.parse_status, "task_id": task_id}
    except Exception as exc:
        document = db.get(Document, document_id)
        if document is not None:
            document.parse_status = "failed"
            db.commit()
        return {"ok": False, "document_id": document_id, "task_id": task_id, "error": str(exc)}
    finally:
        db.close()
