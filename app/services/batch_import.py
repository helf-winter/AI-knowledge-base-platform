from __future__ import annotations

import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.batch import BatchImportJob, BatchImportItem
from app.services.knowledge_service import KnowledgeService
from app.schemas.batch import BatchImportCreate


class BatchImportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_job(self, payload: BatchImportCreate) -> BatchImportJob:
        job = BatchImportJob(
            job_id=str(uuid.uuid4()),
            job_name=payload.job_name,
            source_type=payload.source_type,
            total_files=len(payload.files),
            processed_files=0,
            failed_files=0,
            status="running" if payload.files else "empty",
        )
        self.db.add(job)
        self.db.flush()

        for item in payload.files:
            record = BatchImportItem(
                item_id=str(uuid.uuid4()),
                job_id=job.job_id,
                file_name=item.file_name,
                file_path=item.file_path,
                status="pending",
            )
            self.db.add(record)

        self.db.commit()
        self.db.refresh(job)
        return job

    def process_job(self, job_id: str) -> BatchImportJob:
        job = self.db.get(BatchImportJob, job_id)
        if job is None:
            raise ValueError("batch job not found")

        items = self.db.execute(select(BatchImportItem).where(BatchImportItem.job_id == job_id)).scalars().all()
        service = KnowledgeService(self.db)
        job.status = "running"
        self.db.commit()

        processed = 0
        failed = 0
        for item in items:
            try:
                with open(item.file_path, "rb") as f:
                    content = f.read()
                service.upload_document(item.file_name, content)
                item.status = "succeeded"
                item.error_message = None
                processed += 1
            except Exception as exc:
                item.status = "failed"
                item.error_message = str(exc)
                failed += 1
            self.db.commit()

        job.processed_files = processed
        job.failed_files = failed
        job.status = "completed" if failed == 0 else "completed_with_errors"
        self.db.commit()
        self.db.refresh(job)
        return job

    def list_jobs(self) -> list[BatchImportJob]:
        return list(self.db.execute(select(BatchImportJob)).scalars().all())
