from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class KnowledgeMergeAgentTest(unittest.TestCase):
    def test_merge_suggestion_model_and_migration_exist(self) -> None:
        model = (ROOT / "app" / "models" / "document.py").read_text(encoding="utf-8")
        migration = (ROOT / "alembic" / "versions" / "0021_knowledge_merge_suggestions.py").read_text(encoding="utf-8")

        self.assertIn("class KnowledgeMergeSuggestion", model)
        self.assertIn("knowledge_merge_suggestions", migration)
        self.assertIn("source_document_ids", migration)
        self.assertIn("merged_document_id", migration)

    def test_merge_service_creates_reviewable_suggestions_and_merged_document(self) -> None:
        service = (ROOT / "app" / "services" / "knowledge_merge.py").read_text(encoding="utf-8")

        self.assertIn("class KnowledgeMergeService", service)
        self.assertIn("def scan", service)
        self.assertIn("def review", service)
        self.assertIn("create_manual_knowledge", service)
        self.assertIn("原始文档", service)
        self.assertNotIn("self.db.delete(document)", service)

    def test_merge_routes_are_available_for_user_and_admin(self) -> None:
        routes = (ROOT / "app" / "api" / "routes.py").read_text(encoding="utf-8")

        self.assertIn('/knowledge/merge-suggestions/scan', routes)
        self.assertIn('/knowledge/merge-suggestions/my', routes)
        self.assertIn('/admin/knowledge-merge-suggestions', routes)
        self.assertIn("KnowledgeMergeService", routes)

    def test_admin_page_exposes_merge_agent_workflow(self) -> None:
        page = (ROOT / "frontend" / "src" / "app" / "admin" / "page.tsx").read_text(encoding="utf-8")

        self.assertIn("知识整合 Agent", page)
        self.assertIn("scanKnowledgeMergeSuggestions", page)
        self.assertIn("reviewKnowledgeMergeSuggestion", page)
        self.assertIn("通过并生成整合文档", page)


if __name__ == "__main__":
    unittest.main()
