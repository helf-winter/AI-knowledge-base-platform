from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AdminNavigationVisibilityTest(unittest.TestCase):
    def test_automatic_learning_is_admin_only_across_navigation_and_routes(self) -> None:
        sidebar = (ROOT / "frontend/src/components/layout/sidebar-shell.tsx").read_text(encoding="utf-8")
        auth_guard = (ROOT / "frontend/src/components/auth/auth-guard.tsx").read_text(encoding="utf-8")
        dashboard = (ROOT / "frontend/src/app/page.tsx").read_text(encoding="utf-8")

        self.assertIn("{ href: '/tasks', label: '自动学习', icon: FileUp, adminOnly: true }", sidebar)
        self.assertIn("const ADMIN_PATHS = ['/admin', '/tasks'];", auth_guard)
        self.assertIn("const isAdminPath = ADMIN_PATHS.some", auth_guard)
        self.assertIn("isAdminUser ? (", dashboard)
        self.assertIn("<Link href=\"/tasks\">", dashboard)

    def test_employee_dashboard_reflows_without_admin_content_gaps(self) -> None:
        dashboard = (ROOT / "frontend/src/app/page.tsx").read_text(encoding="utf-8")

        self.assertIn("const summaryGridClass = isAdminUser", dashboard)
        self.assertIn("'grid gap-4 md:grid-cols-2 xl:grid-cols-2'", dashboard)
        self.assertIn("const activityGridClass = isAdminUser", dashboard)
        self.assertIn("'grid gap-6'", dashboard)

    def test_management_group_heading_is_hidden_from_employees(self) -> None:
        sidebar = (ROOT / "frontend/src/components/layout/sidebar-shell.tsx").read_text(encoding="utf-8")

        self.assertIn("{isAdminUser ? (", sidebar)
        self.assertIn(">管理入口</div>", sidebar)


if __name__ == "__main__":
    unittest.main()
