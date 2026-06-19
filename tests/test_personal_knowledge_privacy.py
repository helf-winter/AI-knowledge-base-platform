from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

from app.api.routes import _publish_request_response
from app.services.access_control import DocumentAccessService
from app.services.auth import AuthenticatedUser

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN_PAGE = ROOT / "frontend" / "src" / "app" / "admin" / "page.tsx"
ROUTES_FILE = ROOT / "app" / "api" / "routes.py"

def user(user_id: str, roles: list[str]) -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=user_id,
        username=user_id,
        employee_no=None,
        display_name=user_id,
        email=None,
        department=None,
        position=None,
        permission_level=9 if "admin" in roles else 1,
        is_first_login=False,
        status="active",
        roles=roles,
    )


def personal_document(owner_user_id: str = "owner-1") -> SimpleNamespace:
    return SimpleNamespace(
        document_id="doc-personal",
        owner_user_id=owner_user_id,
        document_status="active",
        knowledge_space="personal",
        visibility="private",
        visibility_type="private",
        is_public=False,
        allowed_job_categories=None,
        allowed_departments=None,
        min_permission_level=1,
    )


class PersonalKnowledgePrivacyTest(unittest.TestCase):
    def test_admin_cannot_directly_access_another_users_unpublished_personal_document(self):
        db = MagicMock()
        db.execute.return_value.scalars.return_value.first.return_value = None
        service = DocumentAccessService(db)

        decision = service.can_access_document(personal_document(), user("admin-1", ["admin"]))

        self.assertFalse(decision.can_access)
        self.assertFalse(decision.need_apply)
        self.assertIn("个人知识", decision.reason)

    def test_owner_can_access_own_personal_document(self):
        db = MagicMock()
        db.execute.return_value.scalars.return_value.first.return_value = None
        service = DocumentAccessService(db)

        decision = service.can_access_document(personal_document(), user("owner-1", ["user"]))

        self.assertTrue(decision.can_access)

    def test_publish_review_response_contains_pending_document_preview(self):
        request = SimpleNamespace(
            request_id="publish-1",
            document_id="doc-personal",
            requester_id="owner-1",
            target_category="IT",
            allowed_job_categories="全公司",
            publish_reason="希望发布给大家使用",
            business_purpose="支撑 VPN 咨询",
            status="pending",
            reviewed_by=None,
            review_comment=None,
            reviewed_at=None,
            created_at=None,
        )
        requester = SimpleNamespace(display_name="张三", employee_no="E1001")
        document = SimpleNamespace(file_name="VPN说明.md", content_text="这是用户主动提交发布的个人知识内容。" * 20)
        service = MagicMock()
        service.get_context.return_value = {"requester": requester, "document": document}

        response = _publish_request_response(request, service)

        self.assertEqual(response.document_name, "VPN说明.md")
        self.assertIn("用户主动提交发布", response.document_content_preview or "")

    def test_publish_review_page_does_not_link_to_private_document_detail(self):
        source = ADMIN_PAGE.read_text(encoding="utf-8")

        self.assertNotIn("/documents/${selectedPublishRequest.document_id}", source)
        self.assertIn("发布审核预览", source)

    def test_admin_metadata_list_uses_role_and_document_access_filter(self):
        source = ROUTES_FILE.read_text(encoding="utf-8")

        self.assertIn('user=Depends(require_roles("admin", "reviewer"))', source)
        self.assertIn("access.can_access_document(document, user).can_access", source)


if __name__ == "__main__":
    unittest.main()
