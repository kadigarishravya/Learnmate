import unittest
from dataclasses import dataclass
from datetime import datetime

from app.api.factory import create_app
from app.config.settings import get_settings
from app.modules.student_management.auth import AuthService


@dataclass
class FakeStudent:
    student_id: int
    name: str
    email: str
    password: str
    registration_date: datetime


class FakeStudentRepository:
    def __init__(self):
        self.students = {}
        self.next_id = 1

    def find_by_email(self, email):
        return next((student for student in self.students.values() if student.email == email), None)

    def get(self, student_id):
        return self.students.get(student_id)

    def create(self, name, email, password_hash, registration_date):
        student = FakeStudent(self.next_id, name, email, password_hash, registration_date)
        self.students[self.next_id] = student
        self.next_id += 1
        return student

    def update_profile(self, student_id, name, email):
        student = self.students.get(student_id)
        if student:
            student.name = name
            student.email = email
        return student


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        self.repository = FakeStudentRepository()
        self.app = create_app(get_settings())
        self.app.config["LEARNMATE_STUDENT_REPOSITORY"] = self.repository
        self.client = self.app.test_client()

    def register(self, name="Student One", email="one@example.com", password="correct-password"):
        return self.client.post(
            "/api/auth/register",
            json={"name": name, "email": email, "password": password},
        )

    def login(self, email="one@example.com", password="correct-password"):
        return self.client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )

    def test_registration_succeeds_without_returning_password(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("password", response.get_json()["student"])
        stored = self.repository.find_by_email("one@example.com")
        self.assertNotEqual(stored.password, "correct-password")

    def test_duplicate_email_is_rejected(self):
        self.register()
        response = self.register(name="Other", email="ONE@example.com")
        self.assertEqual(response.status_code, 409)

    def test_login_succeeds_and_wrong_password_fails(self):
        self.register()
        valid = self.login()
        invalid = self.login(password="wrong-password")
        self.assertEqual(valid.status_code, 200)
        self.assertIn("session_id", valid.get_json())
        self.assertEqual(invalid.status_code, 401)

    def test_protected_profile_requires_authentication(self):
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 401)

    def test_student_only_sees_own_profile(self):
        self.register()
        first_session = self.login().get_json()["session_id"]
        self.register(name="Student Two", email="two@example.com")
        second_session = self.login(email="two@example.com").get_json()["session_id"]

        first_profile = self.client.get(
            "/api/auth/me", headers={"X-Session-ID": first_session}
        ).get_json()["student"]
        second_profile = self.client.get(
            "/api/auth/me", headers={"X-Session-ID": second_session}
        ).get_json()["student"]
        self.assertEqual(first_profile["email"], "one@example.com")
        self.assertEqual(second_profile["email"], "two@example.com")
        self.assertNotEqual(first_profile["student_id"], second_profile["student_id"])

    def test_logout_invalidates_session(self):
        self.register()
        session_id = self.login().get_json()["session_id"]
        logout = self.client.post("/api/auth/logout", headers={"X-Session-ID": session_id})
        profile = self.client.get("/api/auth/me", headers={"X-Session-ID": session_id})
        self.assertEqual(logout.status_code, 200)
        self.assertEqual(profile.status_code, 401)


class AuthServiceTests(unittest.TestCase):
    def test_password_hash_is_verifiable(self):
        repository = FakeStudentRepository()
        AuthService(repository).register("Student", "student@example.com", "a-secure-password")
        self.assertTrue(repository.find_by_email("student@example.com").password.startswith("scrypt:"))