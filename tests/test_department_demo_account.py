from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.core import Department, Role, User, UserRole
from app.services.auth import AuthService
from app.services.access_control import DocumentAccessService


class DepartmentDemoAccountTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        for table in (Department.__table__, Role.__table__, User.__table__, UserRole.__table__):
            table.create(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_seed_adds_hr_employee_without_new_department_role(self) -> None:
        with Session(self.engine) as db:
            AuthService(db).seed_default_admin()

            employee = db.execute(select(User).where(User.employee_no == "E1004")).scalar_one()
            department = db.get(Department, employee.department_id)
            roles = AuthService(db).list_roles(employee.user_id)

            self.assertEqual(employee.display_name, "赵敏")
            self.assertEqual(department.department_name, "人力资源部")
            self.assertEqual(roles, ["user"])
            self.assertNotIn("department", roles)

            authenticated, _ = AuthService(db).login("E1004", "654321")
            self.assertEqual(authenticated.department, "人力资源部")
            self.assertTrue(authenticated.is_first_login)

    def test_department_knowledge_is_visible_only_to_matching_department(self) -> None:
        db = MagicMock()
        db.execute.return_value.scalars.return_value.first.return_value = None
        service = DocumentAccessService(db)
        document = SimpleNamespace(
            document_id="hr-handbook",
            document_status="active",
            owner_user_id=None,
            knowledge_space="department",
            allowed_departments="人力资源部",
            allowed_job_categories=None,
            visibility_type="internal",
            visibility="internal",
            is_public=False,
            min_permission_level=1,
        )
        hr_user = SimpleNamespace(user_id="hr-user", employee_no="E1004", department="人力资源部", permission_level=3, position="人力资源专员", roles=["user"])
        it_user = SimpleNamespace(user_id="it-user", employee_no="E1001", department="信息技术部", permission_level=3, position="研发工程师", roles=["user"])

        self.assertTrue(service.can_access_document(document, hr_user).can_access)
        self.assertFalse(service.can_access_document(document, it_user).can_access)


if __name__ == "__main__":
    unittest.main()
