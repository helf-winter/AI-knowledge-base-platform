from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ROUTES = ROOT / "app" / "api" / "routes.py"
SKILLS_PAGE = ROOT / "frontend" / "src" / "app" / "skills" / "page.tsx"
DOCUMENT_DETAIL_PAGE = ROOT / "frontend" / "src" / "app" / "documents" / "[document_id]" / "page.tsx"


class EmployeeMetadataAccessTest(unittest.TestCase):
    def test_read_only_metadata_endpoint_is_available_to_current_user(self) -> None:
        source = ROUTES.read_text(encoding="utf-8")

        self.assertIn('@router.get("/knowledge/metadata"', source)
        self.assertIn("user=Depends(get_current_user)", source)
        self.assertIn("access.can_access_document(document, user).can_access", source)

    def test_employee_pages_do_not_call_admin_metadata_endpoint_for_read_only_data(self) -> None:
        skills = SKILLS_PAGE.read_text(encoding="utf-8")
        detail = DOCUMENT_DETAIL_PAGE.read_text(encoding="utf-8")

        self.assertIn("/api/v1/knowledge/metadata", skills)
        self.assertIn("/api/v1/knowledge/metadata", detail)
        self.assertNotIn("/api/v1/admin/knowledge-metadata", skills)
        self.assertNotIn("/api/v1/admin/knowledge-metadata", detail)


if __name__ == "__main__":
    unittest.main()
