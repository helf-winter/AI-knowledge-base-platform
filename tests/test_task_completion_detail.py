from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

from app.models.core import TaskRecord
from app.services.task_service import TaskService


class TaskCompletionDetailTest(unittest.TestCase):
    def test_mark_succeeded_replaces_stale_progress_detail(self) -> None:
        task = SimpleNamespace(
            status="running",
            stage="embedding",
            progress_current=1,
            progress_total=1,
            detail="正在生成语义向量",
            error_message=None,
        )
        db = MagicMock()
        db.get.return_value = task

        result = TaskService(db).mark_succeeded("task-1")

        db.get.assert_called_once_with(TaskRecord, "task-1")
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.stage, "completed")
        self.assertEqual(result.detail, "解析完成")


if __name__ == "__main__":
    unittest.main()
