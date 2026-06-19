from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

from app.core.exceptions import PermissionAppError, ValidationAppError
from app.models.conversation import ConversationTurn
from app.services.knowledge_service import KnowledgeService


class FeedbackServiceTest(unittest.TestCase):
    def make_service(self, turn: object | None) -> tuple[KnowledgeService, MagicMock]:
        db = MagicMock()
        db.get.return_value = turn
        return KnowledgeService(db), db

    def test_user_can_record_feedback_for_own_turn(self) -> None:
        turn = SimpleNamespace(
            turn_id="turn-1",
            session_id="session-1",
            user_id="user-1",
        )
        service, db = self.make_service(turn)

        feedback = service.record_feedback(
            session_id="session-1",
            answer_id="turn-1",
            rating=5,
            is_helpful=True,
            user_id="user-1",
        )

        db.get.assert_called_once_with(ConversationTurn, "turn-1")
        db.add.assert_called_once_with(feedback)
        db.commit.assert_called_once()

    def test_missing_turn_is_rejected(self) -> None:
        service, db = self.make_service(None)

        with self.assertRaisesRegex(ValidationAppError, "问答记录不存在"):
            service.record_feedback(
                session_id="session-1",
                answer_id="missing-turn",
                rating=5,
                is_helpful=True,
                user_id="user-1",
            )

        db.add.assert_not_called()

    def test_feedback_for_another_users_turn_is_rejected(self) -> None:
        turn = SimpleNamespace(
            turn_id="turn-1",
            session_id="session-1",
            user_id="user-2",
        )
        service, db = self.make_service(turn)

        with self.assertRaisesRegex(PermissionAppError, "只能评价自己的问答记录"):
            service.record_feedback(
                session_id="session-1",
                answer_id="turn-1",
                rating=5,
                is_helpful=True,
                user_id="user-1",
            )

        db.add.assert_not_called()


if __name__ == "__main__":
    unittest.main()
