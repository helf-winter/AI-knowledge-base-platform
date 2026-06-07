from __future__ import annotations

from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.jobs.noop")
def noop_task(payload: dict) -> dict:
    return {"ok": True, "payload": payload}
