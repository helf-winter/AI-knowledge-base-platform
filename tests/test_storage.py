from pathlib import Path
import tempfile
import unittest

from app.services.storage import save_local_temp


class StorageTests(unittest.TestCase):
    def test_save_local_temp_uses_unique_storage_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            first = Path(save_local_temp("same.pdf", b"first", base_dir=temp_dir))
            second = Path(save_local_temp("same.pdf", b"second", base_dir=temp_dir))

            self.assertNotEqual(first, second)
            self.assertTrue(first.name.endswith("_same.pdf"))
            self.assertTrue(second.name.endswith("_same.pdf"))
            self.assertEqual(first.read_bytes(), b"first")
            self.assertEqual(second.read_bytes(), b"second")


if __name__ == "__main__":
    unittest.main()
