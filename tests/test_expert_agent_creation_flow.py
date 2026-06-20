from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILLS_PAGE = ROOT / "frontend" / "src" / "app" / "skills" / "page.tsx"


class ExpertAgentCreationFlowTest(unittest.TestCase):
    def test_expert_agent_creation_uses_authenticated_request(self) -> None:
        page = SKILLS_PAGE.read_text(encoding="utf-8")

        create_agent_block = page.split("async function createAgent", 1)[1].split("export default", 1)[0]
        self.assertIn("authedFetch(`${API_BASE}/api/v1/admin/expert-agents`", create_agent_block)
        self.assertNotIn("fetch(`${API_BASE}/api/v1/admin/expert-agents`", create_agent_block)

    def test_expert_agent_creation_does_not_route_to_missing_chat_page(self) -> None:
        page = SKILLS_PAGE.read_text(encoding="utf-8")

        self.assertNotIn("router.push(`/chat?", page)
        self.assertIn("setSelectedAgentId", page)


if __name__ == "__main__":
    unittest.main()
