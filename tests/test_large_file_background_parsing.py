from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LargeFileBackgroundParsingTest(unittest.TestCase):
    def test_backend_contains_queue_based_document_parsing(self) -> None:
        service = (ROOT / "app" / "services" / "knowledge_service.py").read_text(encoding="utf-8")
        jobs = (ROOT / "app" / "tasks" / "jobs.py").read_text(encoding="utf-8")
        routes = (ROOT / "app" / "api" / "routes.py").read_text(encoding="utf-8")

        self.assertIn("create_upload_record", service)
        self.assertIn("run_parse_document_task", service)
        self.assertIn("parse_document_task", jobs)
        self.assertIn("enqueue_parse_document", service)
        self.assertIn("/documents/{document_id}/parse/retry", routes)

    def test_task_progress_fields_are_exposed(self) -> None:
        model = (ROOT / "app" / "models" / "core.py").read_text(encoding="utf-8")
        schema = (ROOT / "app" / "schemas" / "task.py").read_text(encoding="utf-8")
        migration = (ROOT / "alembic" / "versions" / "0020_task_progress_fields.py").read_text(encoding="utf-8")

        for field in ["stage", "progress_current", "progress_total", "detail"]:
            self.assertIn(field, model)
            self.assertIn(field, schema)
            self.assertIn(field, migration)

    def test_frontend_shows_document_task_status_and_retry_action(self) -> None:
        page = (ROOT / "frontend" / "src" / "app" / "documents" / "page.tsx").read_text(encoding="utf-8")

        self.assertIn("fetchDocumentTasks", page)
        self.assertIn("retryDocumentParsing", page)
        self.assertIn("解析进度", page)
        self.assertIn("继续解析", page)
        self.assertIn("selectedParseTask.status === 'succeeded' ? '解析完成'", page)

    def test_document_detail_loads_primary_document_before_optional_panels(self) -> None:
        page = (ROOT / "frontend" / "src" / "app" / "documents" / "[document_id]" / "page.tsx").read_text(encoding="utf-8")

        self.assertIn("const item = await fetchDocument", page)
        self.assertIn("Promise.allSettled", page)

    def test_duplicate_upload_is_scoped_to_owner(self) -> None:
        service = (ROOT / "app" / "services" / "knowledge_service.py").read_text(encoding="utf-8")

        self.assertIn("Document.owner_user_id == owner_user_id", service)


if __name__ == "__main__":
    unittest.main()
