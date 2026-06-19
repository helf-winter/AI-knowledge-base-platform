import unittest
from unittest.mock import MagicMock

from app.models.core import KnowledgeMetadata
from app.models.document import Document, DocumentChunk
from app.schemas.knowledge import ManualKnowledgeCreate
from app.services.auth import AuthenticatedUser
from app.services.knowledge_publish import KnowledgePublishService
from app.services.knowledge_service import KnowledgeService


class ManualKnowledgeAuthoringTest(unittest.TestCase):
    def make_service(self) -> tuple[KnowledgeService, MagicMock, list[object]]:
        added: list[object] = []
        db = MagicMock()
        db.add.side_effect = added.append
        db.execute.return_value.scalar_one_or_none.return_value = None
        return KnowledgeService(db), db, added

    def test_creates_personal_markdown_document_with_chunk_and_metadata(self) -> None:
        service, db, added = self.make_service()

        document = service.create_manual_knowledge(
            ManualKnowledgeCreate(
                title="VPN 申请经验",
                content="## 背景\n员工需要访问内网时，应先提交 VPN 权限申请。",
                knowledge_category="IT 流程",
                allowed_job_categories="全公司",
                business_purpose="用于员工自助查询 VPN 申请流程",
                tags="VPN,权限申请",
            ),
            owner_user_id="user-1",
        )

        documents = [item for item in added if isinstance(item, Document)]
        chunks = [item for item in added if isinstance(item, DocumentChunk)]
        metadata = [item for item in added if isinstance(item, KnowledgeMetadata)]

        self.assertIs(document, documents[0])
        self.assertEqual(document.owner_user_id, "user-1")
        self.assertEqual(document.knowledge_space, "personal")
        self.assertEqual(document.visibility_scope, "owner")
        self.assertEqual(document.publish_status, "none")
        self.assertEqual(document.file_type, "md")
        self.assertEqual(document.parse_status, "succeeded")
        self.assertEqual(document.knowledge_category, "IT 流程")
        self.assertIn("# VPN 申请经验", document.content_text)
        self.assertIn("适用人员：全公司", document.content_text)
        self.assertIn("业务用途：用于员工自助查询 VPN 申请流程", document.content_text)
        self.assertEqual(len(chunks), 1)
        self.assertIn("员工需要访问内网", chunks[0].content)
        self.assertEqual(len(metadata), 1)
        self.assertEqual(metadata[0].source_type, "manual")
        self.assertEqual(metadata[0].knowledge_type, "IT 流程")
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(document)

    def test_rejects_blank_manual_content(self) -> None:
        service, db, _added = self.make_service()

        with self.assertRaisesRegex(Exception, "正文不能为空"):
            service.create_manual_knowledge(
                ManualKnowledgeCreate(title="VPN", content="   ", knowledge_category="IT"),
                owner_user_id="user-1",
            )

        db.add.assert_not_called()

    def test_manual_knowledge_can_enter_existing_publish_flow(self) -> None:
        service, _db, _added = self.make_service()
        document = service.create_manual_knowledge(
            ManualKnowledgeCreate(
                title="VPN 申请经验",
                content="员工需要访问内网时，应先提交 VPN 权限申请。",
                knowledge_category="IT 流程",
                allowed_job_categories="全公司",
                business_purpose="用于员工自助查询 VPN 申请流程",
            ),
            owner_user_id="user-1",
        )

        publish_service = KnowledgePublishService(MagicMock())
        publish_service.db.get.return_value = document

        request = publish_service.create_request(
            payload=MagicMock(
                document_id=document.document_id,
                target_category="IT 流程",
                allowed_job_categories="全公司",
                publish_reason="这条个人经验已经整理成流程，适合发布给全公司使用。",
                business_purpose="减少 VPN 申请咨询成本。",
            ),
            user=AuthenticatedUser(
                user_id="user-1",
                username="zhangsan",
                employee_no="E1001",
                display_name="张三",
                email=None,
                department=None,
                position=None,
                permission_level=1,
                is_first_login=False,
                status="active",
                roles=["user"],
            ),
        )

        self.assertEqual(request.document_id, document.document_id)
        self.assertEqual(document.publish_status, "pending")


if __name__ == "__main__":
    unittest.main()
