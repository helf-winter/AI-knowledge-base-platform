from __future__ import annotations

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Knowledge Base"
    environment: str = Field(default="development")
    api_prefix: str = "/api/v1"
    database_url: str = Field(default="sqlite+pysqlite:///./knowledge.db")
    redis_url: str = Field(default="redis://localhost:6379/0")
    minio_endpoint: str = Field(default="localhost:9000")
    minio_access_key: str = Field(default="minioadmin")
    minio_secret_key: str = Field(default="minioadmin")
    minio_bucket: str = Field(default="knowledge")
    deepseek_api_key: str | None = Field(default=None)
    deepseek_base_url: str = Field(default="https://api.deepseek.com")
    deepseek_model: str = Field(default="deepseek-v4-flash")
    deepseek_thinking_enabled: bool = Field(default=True)
    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 100
    embedding_dimension: int = 64
    max_upload_size_mb: int = 20
    tesseract_cmd: str | None = Field(default=None)


@lru_cache
def get_settings() -> Settings:
    return Settings()
