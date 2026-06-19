from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

from app.core.exceptions import PermissionAppError, ValidationAppError
from app.models.document import PublicKnowledgeSuggestion
from app.schemas.knowledge import PublicKnowledgeSuggestionCreate, PublicKnowledgeSuggestionReview
from app.services.auth import AuthenticatedUser
from app.services.knowledge_publish import KnowledgeSuggestionService


def user(user_id: str, roles: list[str] | None = None) -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=user_id,
        username=user_id,
        employee_no=user_id,
        display_name=user_id,
        email=None,
        department=None,
        position=None,
        permission_level=9 if roles and "admin" in roles else 1,
        is_first_login=False,
        status="active",
        roles=roles or ["user"],
    )


class PublicKnowledgeSuggestionTest(unittest.TestCase):
    def test_employee_can_submit_suggestion_for_accessible_public_knowledge(self) -> None:
        document = SimpleNamespace(document_id="doc-1", file_name="VPN.md")
        access = MagicMock()
        access.can_access_document.return_value = SimpleNamespace(can_access=True, public_ref_id="ref-1")
        db = MagicMock()
        db.get.return_value = document
        added: list[object] = []
        db.add.side_effect = added.append

        item = KnowledgeSuggestionService(db, access).create_suggestion(
            PublicKnowledgeSuggestionCreate(
                document_id="doc-1",
                suggestion_type="missing_steps",
                question="VPN 申请入口在哪里？",
                suggestion="建议补充 IT 服务台申请入口和审批时长。",
                business_impact="减少员工反复咨询。",
            ),
            requester=user("u1"),
        )

        self.assertIs(item, added[0])
        self.assertIsInstance(item, PublicKnowledgeSuggestion)
        self.assertEqual(item.document_id, "doc-1")
        self.assertEqual(item.public_ref_id, "ref-1")
        self.assertEqual(item.requester_id, "u1")
        self.assertEqual(item.status, "pending")
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(item)

    def test_employee_cannot_submit_suggestion_for_non_public_knowledge(self) -> None:
        document = SimpleNamespace(document_id="doc-1", file_name="VPN.md")
        access = MagicMock()
        access.can_access_document.return_value = SimpleNamespace(can_access=True, public_ref_id=None)
        db = MagicMock()
        db.get.return_value = document

        with self.assertRaisesRegex(ValidationAppError, "只能对公有知识提交建议"):
            KnowledgeSuggestionService(db, access).create_suggestion(
                PublicKnowledgeSuggestionCreate(
                    document_id="doc-1",
                    suggestion_type="content_error",
                    question="这里是不是错了？",
                    suggestion="建议核对。",
                    business_impact="避免误导员工。",
                ),
                requester=user("u1"),
            )

        db.add.assert_not_called()

    def test_admin_can_mark_pending_suggestion_as_accepted(self) -> None:
        item = PublicKnowledgeSuggestion(
            suggestion_id="s1",
            document_id="doc-1",
            requester_id="u1",
            suggestion_type="content_error",
            question="这里是不是错了？",
            suggestion="建议改正。",
            business_impact="避免误导。",
            status="pending",
        )
        db = MagicMock()
        db.get.return_value = item

        reviewed = KnowledgeSuggestionService(db).review_suggestion(
            "s1",
            PublicKnowledgeSuggestionReview(status="accepted", review_comment="采纳，后续修订。"),
            reviewer=user("admin", ["admin"]),
        )

        self.assertEqual(reviewed.status, "accepted")
        self.assertEqual(reviewed.reviewed_by, "admin")
        self.assertEqual(reviewed.review_comment, "采纳，后续修订。")
        self.assertIsNotNone(reviewed.reviewed_at)
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(item)

    def test_reviewed_suggestion_cannot_be_reviewed_again(self) -> None:
        item = PublicKnowledgeSuggestion(
            suggestion_id="s1",
            document_id="doc-1",
            requester_id="u1",
            suggestion_type="content_error",
            question="这里是不是错了？",
            suggestion="建议改正。",
            business_impact="避免误导。",
            status="accepted",
        )
        db = MagicMock()
        db.get.return_value = item

        with self.assertRaisesRegex(ValidationAppError, "已处理的建议不能重复处理"):
            KnowledgeSuggestionService(db).review_suggestion(
                "s1",
                PublicKnowledgeSuggestionReview(status="rejected", review_comment="不采纳。"),
                reviewer=user("admin", ["admin"]),
            )

    def test_non_admin_cannot_review_suggestion(self) -> None:
        db = MagicMock()

        with self.assertRaises(PermissionAppError):
            KnowledgeSuggestionService(db).review_suggestion(
                "s1",
                PublicKnowledgeSuggestionReview(status="accepted", review_comment="采纳。"),
                reviewer=user("u1", ["user"]),
            )


if __name__ == "__main__":
    unittest.main()
