from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILLS_PAGE = ROOT / "frontend" / "src" / "app" / "skills" / "page.tsx"
ADMIN_SERVICE = ROOT / "app" / "services" / "knowledge_admin.py"


class BusinessAgentSkillExperienceTest(unittest.TestCase):
    def test_skill_catalog_uses_business_actions(self) -> None:
        service = ADMIN_SERVICE.read_text(encoding="utf-8")

        for label in ["查找制度依据", "总结文档", "提取流程步骤", "发现知识缺口", "生成发布草稿"]:
            self.assertIn(label, service)

    def test_expert_agent_page_generates_agent_config_from_selected_knowledge(self) -> None:
        page = SKILLS_PAGE.read_text(encoding="utf-8")

        self.assertIn("selectedKnowledgeIds", page)
        self.assertIn("generateAgentDraft", page)
        self.assertIn("document_ids", page)
        self.assertIn("适合回答的问题", page)
        self.assertIn("回答边界", page)

    def test_expert_agent_cards_explain_role_scope_and_skills(self) -> None:
        page = SKILLS_PAGE.read_text(encoding="utf-8")

        self.assertIn("专家职责", page)
        self.assertIn("绑定知识", page)
        self.assertIn("启用能力", page)
        self.assertIn("createDefaultAgentScope", page)


if __name__ == "__main__":
    unittest.main()
