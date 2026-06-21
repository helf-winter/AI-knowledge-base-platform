from types import SimpleNamespace
from pathlib import Path
import unittest
from unittest.mock import MagicMock

from app.core.exceptions import PermissionAppError
from app.services.knowledge_service import KnowledgeService


ROOT = Path(__file__).resolve().parents[1]


class DocumentDeletionPermissionTest(unittest.TestCase):
    def make_service(self, document: object) -> tuple[KnowledgeService, MagicMock]:
        service = KnowledgeService.__new__(KnowledgeService)
        service.db = MagicMock()
        service.get_document = MagicMock(return_value=document)
        return service, service.db

    def test_owner_can_delete_own_personal_document(self) -> None:
        document = SimpleNamespace(document_id="doc-1", owner_user_id="user-1", knowledge_space="personal")
        user = SimpleNamespace(user_id="user-1", roles=["user"])
        service, db = self.make_service(document)

        result = service.delete_document("doc-1", user)

        self.assertIs(result, document)
        db.delete.assert_called_once_with(document)
        db.commit.assert_called_once()

    def test_employee_cannot_delete_another_users_document(self) -> None:
        document = SimpleNamespace(document_id="doc-1", owner_user_id="user-2", knowledge_space="personal")
        user = SimpleNamespace(user_id="user-1", roles=["user"])
        service, db = self.make_service(document)

        with self.assertRaisesRegex(PermissionAppError, "只能删除自己创建的文档"):
            service.delete_document("doc-1", user)

        db.delete.assert_not_called()

    def test_admin_cannot_delete_another_users_personal_document(self) -> None:
        document = SimpleNamespace(document_id="doc-1", owner_user_id="user-2", knowledge_space="personal")
        admin = SimpleNamespace(user_id="admin-1", roles=["admin"])
        service, db = self.make_service(document)

        with self.assertRaisesRegex(PermissionAppError, "不能删除其他用户的个人知识"):
            service.delete_document("doc-1", admin)

        db.delete.assert_not_called()

    def test_admin_can_delete_non_personal_document(self) -> None:
        document = SimpleNamespace(document_id="doc-1", owner_user_id="user-2", knowledge_space="public")
        admin = SimpleNamespace(user_id="admin-1", roles=["admin"])
        service, db = self.make_service(document)

        result = service.delete_document("doc-1", admin)

        self.assertIs(result, document)
        db.delete.assert_called_once_with(document)

    def test_delete_route_uses_current_user_instead_of_admin_only_role(self) -> None:
        routes = (ROOT / "app" / "api" / "routes.py").read_text(encoding="utf-8")

        route_start = routes.index('@router.delete("/documents/{document_id}"')
        route_end = routes.index('@router.get("/tasks"', route_start)
        delete_route = routes[route_start:route_end]

        self.assertIn("Depends(get_current_user)", delete_route)
        self.assertIn("delete_document(document_id, user)", delete_route)
        self.assertNotIn('require_roles("admin")', delete_route)

    def test_frontend_only_shows_delete_for_owner_or_manageable_document(self) -> None:
        page = (ROOT / "frontend" / "src" / "app" / "documents" / "page.tsx").read_text(encoding="utf-8")

        self.assertIn("function canDeleteDocument", page)
        self.assertIn("canDeleteDocument(selectedDocument) &&", page)


if __name__ == "__main__":
    unittest.main()
