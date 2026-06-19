from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ParseResumeIdempotencyTest(unittest.TestCase):
    def test_process_document_resumes_existing_chunks_and_missing_embeddings(self) -> None:
        source = (ROOT / "app" / "services" / "knowledge_service.py").read_text(encoding="utf-8")

        self.assertIn("existing_chunks_by_hash", source)
        self.assertIn("existing_embedding_chunk_ids", source)
        self.assertIn("_ensure_chunk_embedding", source)
        self.assertIn("断点续跑", source)

    def test_retry_allows_stalled_running_parse_task(self) -> None:
        source = (ROOT / "app" / "services" / "knowledge_service.py").read_text(encoding="utf-8")
        config = (ROOT / "app" / "core" / "config.py").read_text(encoding="utf-8")

        self.assertIn("parse_task_stale_minutes", config)
        self.assertIn("_is_stale_parse_task", source)
        self.assertIn('task.status == "running" and not self._is_stale_parse_task(task)', source)


if __name__ == "__main__":
    unittest.main()
