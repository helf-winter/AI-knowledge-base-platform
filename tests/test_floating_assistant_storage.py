from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ASSISTANT_FILE = ROOT / "frontend" / "src" / "components" / "layout" / "floating-assistant.tsx"


class FloatingAssistantStorageTest(unittest.TestCase):
    def test_message_storage_is_scoped_by_user(self):
        source = ASSISTANT_FILE.read_text(encoding="utf-8")

        self.assertIn("function getAssistantMessagesKey(userId: string)", source)
        self.assertIn("getAssistantMessagesKey(getCurrentUserId() || 'anonymous')", source)
        self.assertNotIn("localStorage.getItem(STORAGE_KEY)", source)
        self.assertNotIn("localStorage.setItem(STORAGE_KEY", source)
        self.assertNotIn("localStorage.removeItem(STORAGE_KEY)", source)


if __name__ == "__main__":
    unittest.main()
