from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api.routes import router
from app.core.config import get_settings
from app.core.database import Base, engine, SessionLocal
from app.core.logging import configure_logging
from app.services.auth import AuthService

# Import models and skills so they register themselves.
from app.skills import registry  # noqa: F401
from app.skills import knowledge_search  # noqa: F401
from app.skills import document_summarize  # noqa: F401
from app.skills import knowledge_extract  # noqa: F401
from app.skills import knowledge_compare  # noqa: F401
from app.skills import knowledge_gap_detect  # noqa: F401
from app.skills import permission_check  # noqa: F401
from app.models import (  # noqa: F401
    core,
    document,
    vector,
    flywheel,
    evaluation,
    observability,
    batch,
    conversation,
)

settings = get_settings()
configure_logging()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix=settings.api_prefix)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _ensure_evaluation_columns() -> None:
    inspector = inspect(engine)
    if "evaluation_runs" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("evaluation_runs")}
    with engine.begin() as conn:
        if "passed_cases" not in existing_columns:
            conn.execute(text("ALTER TABLE evaluation_runs ADD COLUMN passed_cases INTEGER NOT NULL DEFAULT 0"))
        if "failed_cases" not in existing_columns:
            conn.execute(text("ALTER TABLE evaluation_runs ADD COLUMN failed_cases INTEGER NOT NULL DEFAULT 0"))
        if "summary_json" not in existing_columns:
            conn.execute(text("ALTER TABLE evaluation_runs ADD COLUMN summary_json TEXT"))
        if "status" not in existing_columns:
            conn.execute(text("ALTER TABLE evaluation_runs ADD COLUMN status VARCHAR(32) NOT NULL DEFAULT 'pending'"))


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_evaluation_columns()
    db = SessionLocal()
    try:
        AuthService(db).seed_default_admin()
    finally:
        db.close()
