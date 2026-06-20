from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

from app.services.knowledge_taxonomy_backfill import KnowledgeTaxonomyBackfillService


ROOT = Path(__file__).resolve().parents[1]


class KnowledgeTaxonomyBackfillTest(unittest.TestCase):
    def test_existing_category_and_structured_tags_are_not_overwritten(self) -> None:
        service = KnowledgeTaxonomyBackfillService(MagicMock(), deepseek_client=MagicMock())
        document = self._document(category="已有类别")

        item = service._make_plan_item(
            document,
            existing_tags=["已有标签"],
            suggestion={"category": "AI类别", "tags": ["AI标签"]},
            method="deepseek",
        )

        self.assertEqual(item["category"], "已有类别")
        self.assertEqual(item["tags"], ["已有标签"])
        self.assertFalse(item["category_changed"])
        self.assertFalse(item["tags_changed"])

    def test_missing_category_and_tags_use_ai_suggestion(self) -> None:
        service = KnowledgeTaxonomyBackfillService(MagicMock(), deepseek_client=MagicMock())
        document = self._document(category=None)

        item = service._make_plan_item(
            document,
            existing_tags=[],
            suggestion={"category": "IT与技术", "tags": ["VPN", "远程办公", "VPN"]},
            method="deepseek",
        )

        self.assertEqual(item["category"], "IT与技术")
        self.assertEqual(item["tags"], ["VPN", "远程办公"])
        self.assertTrue(item["category_changed"])
        self.assertTrue(item["tags_changed"])

    def test_rule_fallback_classifies_known_topics(self) -> None:
        service = KnowledgeTaxonomyBackfillService(MagicMock(), deepseek_client=MagicMock())

        vpn = service._fallback_suggestion(self._document(file_name="VPN申请指南.md", content="远程办公 VPN 权限申请"))
        frontend = service._fallback_suggestion(self._document(file_name="Vue性能优化面试题.pdf", content="Vue 前端性能优化"))

        self.assertEqual(vpn["category"], "IT与技术")
        self.assertIn("VPN", vpn["tags"])
        self.assertEqual(frontend["category"], "研发知识")
        self.assertIn("前端", frontend["tags"])

    def test_script_supports_plan_then_apply_without_second_ai_call(self) -> None:
        script = (ROOT / "scripts" / "backfill_knowledge_taxonomy.py").read_text(encoding="utf-8")

        self.assertIn("--plan-file", script)
        self.assertIn("--apply-plan", script)
        self.assertIn("build_plan", script)
        self.assertIn("apply_plan", script)

    def _document(self, file_name: str = "VPN指南.md", content: str = "VPN 使用知识", category: str | None = None) -> SimpleNamespace:
        return SimpleNamespace(
            document_id="doc-1",
            file_name=file_name,
            file_type=file_name.rsplit(".", 1)[-1],
            content_text=content,
            knowledge_category=category,
        )


if __name__ == "__main__":
    unittest.main()
