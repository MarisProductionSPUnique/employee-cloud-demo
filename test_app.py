import unittest

from app import create_app, db


class EmployeeApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SQLALCHEMY_ENGINE_OPTIONS": {},
                "AUTO_CREATE_TABLES": True,
                "SEED_DEMO_DATA": False,
                "DEMO_MODE": True,
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    @staticmethod
    def employee_payload(code="EMP2001", email="student@example.com"):
        return {
            "employee_code": code,
            "name": "Student User",
            "email": email,
            "department": "Application Support",
            "role": "Support Analyst",
            "status": "Active",
            "notes": "Classroom record",
        }

    def test_health_returns_database_connection(self):
        response = self.client.get("/api/health", headers={"X-Request-ID": "CLASS-HEALTH"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Request-ID"], "CLASS-HEALTH")
        self.assertEqual(response.get_json()["database"], "connected")

    def test_home_page_and_static_assets_load(self):
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Employee Operations Lab", page.data)
        self.assertIn("default-src 'self'", page.headers["Content-Security-Policy"])
        script = self.client.get("/static/app.js")
        stylesheet = self.client.get("/static/styles.css")
        self.assertEqual(script.status_code, 200)
        self.assertEqual(stylesheet.status_code, 200)
        script.close()
        stylesheet.close()

    def test_complete_crud_flow(self):
        created = self.client.post("/api/employees", json=self.employee_payload())
        self.assertEqual(created.status_code, 201)
        employee_id = created.get_json()["data"]["id"]

        listed = self.client.get("/api/employees")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.get_json()["count"], 1)

        updated_payload = self.employee_payload()
        updated_payload["role"] = "Senior Support Analyst"
        updated = self.client.put(f"/api/employees/{employee_id}", json=updated_payload)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()["data"]["role"], "Senior Support Analyst")

        deleted = self.client.delete(f"/api/employees/{employee_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.client.get("/api/employees").get_json()["count"], 0)

    def test_duplicate_employee_returns_409(self):
        self.assertEqual(self.client.post("/api/employees", json=self.employee_payload()).status_code, 201)
        duplicate = self.client.post(
            "/api/employees",
            json=self.employee_payload(code="EMP2002"),
        )
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.get_json()["error"]["code"], "DUPLICATE_EMPLOYEE")

    def test_validation_returns_400(self):
        response = self.client.post("/api/employees", json={"name": "Only a name"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("employee_code", response.get_json()["error"]["fields"])

    def test_teaching_endpoints(self):
        self.assertEqual(self.client.get("/api/not-found").status_code, 404)
        self.assertEqual(self.client.get("/api/demo/error").status_code, 500)


if __name__ == "__main__":
    unittest.main()
