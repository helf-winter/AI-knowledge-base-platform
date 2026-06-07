from __future__ import annotations

import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundAppError, ValidationAppError
from app.models.core import TaskRecord


class TaskService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_task(self, task_type: str, related_document_id: str | None = None) -> TaskRecord:
        task = TaskRecord(
            task_id=str(uuid.uuid4()),
            task_type=task_type,
            related_document_id=related_document_id,
            status="pending",
            retry_count=0,
            error_message=None,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def mark_running(self, task_id: str) -> TaskRecord:
        task = self._get_task(task_id)
        task.status = "running"
        self.db.commit()
        self.db.refresh(task)
        return task

    def mark_succeeded(self, task_id: str) -> TaskRecord:
        task = self._get_task(task_id)
        task.status = "succeeded"
        task.error_message = None
        self.db.commit()
        self.db.refresh(task)
        return task

    def mark_failed(self, task_id: str, error_message: str) -> TaskRecord:
        task = self._get_task(task_id)
        task.status = "failed"
        task.error_message = error_message
        task.retry_count += 1
        self.db.commit()
        self.db.refresh(task)
        return task

    def retry_task(self, task_id: str) -> TaskRecord:
        task = self._get_task(task_id)
        if not task.related_document_id:
            raise ValidationAppError("任务未关联文档，无法重跑")
        if task.status == "running":
            raise ValidationAppError("任务正在执行中，不能重复重跑")
        task.status = "pending"
        task.error_message = None
        task.retry_count += 1
        self.db.commit()
        self.db.refresh(task)
        return task

    def _get_task(self, task_id: str) -> TaskRecord:
        task = self.db.get(TaskRecord, task_id)
        if task is None:
            raise NotFoundAppError("任务不存在")
        return task

    def list_tasks(self, status: str | None = None, related_document_id: str | None = None) -> list[TaskRecord]:
        stmt = select(TaskRecord)
        if status:
            stmt = stmt.where(TaskRecord.status == status)
        if related_document_id:
            stmt = stmt.where(TaskRecord.related_document_id == related_document_id)
        stmt = stmt.order_by(TaskRecord.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())
