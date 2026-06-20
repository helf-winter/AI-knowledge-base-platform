from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

from app.services.knowledge_merge import KnowledgeMergeService


ROOT = Path(__file__).resolve().parents[1]


class KnowledgeMergeAIUpgradeTest(unittest.TestCase):
    def test_pgvector_is_used_to_find_similar_document_candidates(self) -> None:
        service = (ROOT / "app" / "services" / "knowledge_merge.py").read_text(encoding="utf-8")
        config = (ROOT / "app" / "core" / "config.py").read_text(encoding="utf-8")

        self.assertIn("ChunkEmbedding", service)
        self.assertIn("cosine_distance", service)
        self.assertIn("_vector_candidate_pairs", service)
        self.assertIn("knowledge_merge_max_suggestions", config)
        self.assertIn("knowledge_merge_max_suggestions", service)

    def test_deepseek_generates_structured_merge_draft_with_conflicts_and_sources(self) -> None:
        deepseek = MagicMock()
        deepseek.complete_json.return_value = {
            "title": "VPN 整合指南",
            "category": "IT流程",
            "outline": ["申请", "连接", "故障排查"],
            "merged_content": "# VPN 整合指南\n\n申请流程见[来源1]，连接步骤见[来源2]。",
            "conflicts": [{"topic": "账号来源", "detail": "两份文档描述不同", "recommendation": "请管理员确认"}],
            "source_attributions": [{"section": "申请", "source_ids": ["doc-1"]}],
        }
        service = KnowledgeMergeService(MagicMock(), deepseek_client=deepseek)

        draft = service._build_merge_draft(self._document("doc-1", "VPN申请.md"), self._document("doc-2", "VPN连接.md"), 0.88)

        self.assertEqual(draft["generation_method"], "deepseek")
        self.assertIn("[来源1]", draft["suggested_content"])
        self.assertIn("账号来源", draft["conflict_notes"])
        self.assertIn("doc-1", draft["source_attributions"])

    def test_rule_fallback_keeps_merge_workflow_available(self) -> None:
        deepseek = MagicMock()
        deepseek.complete_json.return_value = None
        service = KnowledgeMergeService(MagicMock(), deepseek_client=deepseek)

        draft = service._build_merge_draft(self._document("doc-1", "VPN申请.md"), self._document("doc-2", "VPN连接.md"), 0.72)

        self.assertEqual(draft["generation_method"], "rule_fallback")
        self.assertIn("doc-1", draft["source_attributions"])
        self.assertTrue(draft["suggested_content"])

    def test_review_can_archive_sources_but_never_deletes_them(self) -> None:
        schemas = (ROOT / "app" / "schemas" / "knowledge.py").read_text(encoding="utf-8")
        service = (ROOT / "app" / "services" / "knowledge_merge.py").read_text(encoding="utf-8")
        search = (ROOT / "app" / "services" / "search.py").read_text(encoding="utf-8")
        page = (ROOT / "frontend" / "src" / "app" / "admin" / "page.tsx").read_text(encoding="utf-8")

        self.assertIn("archive_sources", schemas)
        self.assertIn("_archive_source_documents", service)
        self.assertIn('document.document_status = "archived"', service)
        self.assertNotIn("self.db.delete(document)", service)
        self.assertIn('Document.document_status == "active"', search)
        self.assertIn("同时归档来源文档", page)

    def test_merge_suggestion_persists_generation_details(self) -> None:
        model = (ROOT / "app" / "models" / "document.py").read_text(encoding="utf-8")
        migration = (ROOT / "alembic" / "versions" / "0022_upgrade_knowledge_merge_agent.py").read_text(encoding="utf-8")

        for field in ("generation_method", "conflict_notes", "source_attributions"):
            self.assertIn(field, model)
            self.assertIn(field, migration)

    def _document(self, document_id: str, file_name: str) -> SimpleNamespace:
        return SimpleNamespace(
            document_id=document_id,
            file_name=file_name,
            knowledge_category="IT流程",
            content_text=f"{file_name} 的测试内容，包含申请步骤和使用说明。",
        )


if __name__ == "__main__":
    unittest.main()
