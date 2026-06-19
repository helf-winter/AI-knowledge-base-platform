from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

from app.models.core import ExpertAgentProfile
from app.services.deepseek import DeepSeekClient
from app.services.expert_agent_runtime import ExpertAgentRuntime
from app.skills.knowledge_search import KnowledgeSearchSkill


class DynamicExpertAgentTest(unittest.TestCase):
    def test_explicit_agent_id_resolves_active_profile_context(self) -> None:
        profile = ExpertAgentProfile(
            agent_id="agent-1",
            agent_name="VPN 专家",
            domain_name="IT 支持",
            description="负责 VPN、账号和远程办公问题",
            knowledge_scope_json='{"document_ids": ["doc-vpn"]}',
            skills_json='["knowledge_search", "knowledge_extract"]',
            status="active",
        )
        db = MagicMock()
        db.get.return_value = profile

        context = ExpertAgentRuntime(db).resolve(question="VPN 如何申请？", agent_id="agent-1")

        self.assertIsNotNone(context)
        assert context is not None
        self.assertEqual(context.agent_id, "agent-1")
        self.assertEqual(context.agent_name, "VPN 专家")
        self.assertEqual(context.document_ids, {"doc-vpn"})
        self.assertEqual(context.skills, ["knowledge_search", "knowledge_extract"])
        self.assertIn("用户主动选择", context.selection_reason)

    def test_knowledge_scope_document_id_filters_search_results(self) -> None:
        skill = KnowledgeSearchSkill(MagicMock())
        skill.retriever.search = MagicMock(return_value=[
            self._hit("doc-vpn", "VPN 使用指南", "VPN 内容", 0.91),
            self._hit("doc-hr", "入职指南", "入职内容", 0.89),
        ])

        result = skill.execute("VPN", top_k=5, scope={"document_ids": ["doc-vpn"]})

        self.assertEqual([item["document_id"] for item in result.output["results"]], ["doc-vpn"])

    def test_deepseek_prompt_contains_expert_identity(self) -> None:
        messages = DeepSeekClient().build_messages(
            "VPN 如何申请？",
            ["VPN 申请需要提交工单"],
            expert_context={
                "agent_name": "VPN 专家",
                "domain_name": "IT 支持",
                "description": "负责 VPN 申请和远程办公问题",
                "knowledge_scope": "doc-vpn",
            },
        )

        system_prompt = messages[0]["content"]
        self.assertIn("VPN 专家", system_prompt)
        self.assertIn("IT 支持", system_prompt)
        self.assertIn("负责 VPN 申请", system_prompt)

    def _hit(self, document_id: str, file_name: str, content: str, score: float) -> SimpleNamespace:
        document = SimpleNamespace(
            document_id=document_id,
            file_name=file_name,
            knowledge_category=None,
            allowed_job_categories=None,
        )
        chunk = SimpleNamespace(
            chunk_id=f"chunk-{document_id}",
            document_id=document_id,
            chunk_index=0,
            content=content,
            page_start=None,
            page_end=None,
            document=document,
        )
        return SimpleNamespace(chunk=chunk, final_score=score)


if __name__ == "__main__":
    unittest.main()
