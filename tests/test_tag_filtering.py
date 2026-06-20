from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

from app.models.core import DocumentTag, Tag
from app.schemas.knowledge import ManualKnowledgeCreate, SearchRequest
from app.services.knowledge_service import KnowledgeService
from app.skills.knowledge_search import KnowledgeSearchSkill


class TagFilteringTest(unittest.TestCase):
    def test_search_request_accepts_structured_filters(self) -> None:
        payload = SearchRequest(
            query="VPN",
            user_id="user-1",
            knowledge_categories=["IT流程"],
            tags=["远程办公", "权限申请"],
            knowledge_spaces=["public"],
            file_types=["md", "pdf"],
            allowed_job_categories=["全公司"],
        )

        self.assertEqual(payload.knowledge_categories, ["IT流程"])
        self.assertEqual(payload.tags, ["远程办公", "权限申请"])
        self.assertEqual(payload.knowledge_spaces, ["public"])
        self.assertEqual(payload.file_types, ["md", "pdf"])
        self.assertEqual(payload.allowed_job_categories, ["全公司"])

    def test_skill_filters_by_category_tags_space_file_type_and_allowed_jobs(self) -> None:
        skill = KnowledgeSearchSkill(MagicMock())
        skill.retriever.search = MagicMock(
            return_value=[
                self._hit("doc-vpn", "VPN指南.md", "VPN 远程办公", 0.9, category="IT流程", tags=["远程办公", "权限申请"], space="public", file_type="md", allowed_jobs="全公司"),
                self._hit("doc-hr", "入职指南.pdf", "入职流程", 0.8, category="HR制度", tags=["入职"], space="public", file_type="pdf", allowed_jobs="全公司"),
                self._hit("doc-private", "VPN私人.md", "VPN 个人记录", 0.7, category="IT流程", tags=["远程办公"], space="personal", file_type="md", allowed_jobs="研发部"),
            ]
        )

        result = skill.execute(
            "VPN",
            top_k=5,
            scope={
                "knowledge_categories": ["IT流程"],
                "tags": ["远程办公"],
                "knowledge_spaces": ["public"],
                "file_types": ["md"],
                "allowed_job_categories": ["全公司"],
            },
        )

        self.assertEqual([item["document_id"] for item in result.output["results"]], ["doc-vpn"])

    def test_manual_knowledge_writes_tags_to_structured_tables(self) -> None:
        added: list[object] = []
        db = MagicMock()
        db.add.side_effect = added.append
        db.execute.return_value.scalar_one_or_none.return_value = None

        KnowledgeService(db).create_manual_knowledge(
            ManualKnowledgeCreate(
                title="VPN申请经验",
                content="员工申请 VPN 前需要说明业务用途。",
                knowledge_category="IT流程",
                tags="VPN, 权限申请，远程办公,VPN",
            ),
            owner_user_id="user-1",
        )

        tags = [item for item in added if isinstance(item, Tag)]
        links = [item for item in added if isinstance(item, DocumentTag)]

        self.assertEqual([item.tag_name for item in tags], ["VPN", "权限申请", "远程办公"])
        self.assertEqual(len(links), 3)
        self.assertEqual({item.document_id for item in links}, {links[0].document_id})

    def test_documents_page_sends_filter_payload_and_loads_filter_options(self) -> None:
        with open("frontend/src/app/documents/page.tsx", encoding="utf-8") as file:
            page = file.read()

        self.assertIn("fetchKnowledgeFilterOptions", page)
        self.assertIn("knowledge_categories: searchFilters.knowledgeCategories", page)
        self.assertIn("tags: searchFilters.tags", page)
        self.assertIn("knowledge_spaces: searchFilters.knowledgeSpaces", page)
        self.assertIn("file_types: searchFilters.fileTypes", page)
        self.assertIn("allowed_job_categories: searchFilters.allowedJobCategories", page)
        self.assertIn("标签筛选", page)

    def _hit(
        self,
        document_id: str,
        file_name: str,
        content: str,
        score: float,
        category: str,
        tags: list[str],
        space: str,
        file_type: str,
        allowed_jobs: str,
    ) -> SimpleNamespace:
        document = SimpleNamespace(
            document_id=document_id,
            file_name=file_name,
            knowledge_category=category,
            knowledge_space=space,
            file_type=file_type,
            allowed_job_categories=allowed_jobs,
            tags=tags,
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
