from __future__ import annotations

from pydantic import BaseModel, Field


class BatchFileItem(BaseModel):
    file_name: str
    file_path: str


class BatchImportCreate(BaseModel):
    job_name: str = Field(min_length=1, max_length=128)
    source_type: str = Field(default="upload", max_length=32)
    files: list[BatchFileItem]


class BatchImportRead(BaseModel):
    job_id: str
    job_name: str
    source_type: str
    total_files: int
    processed_files: int
    failed_files: int
    status: str
    error_message: str | None = None
