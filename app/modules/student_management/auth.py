"""Student registration, login, profile, and server-session services."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class ValidationError(ValueError):
    pass


class DuplicateEmailError(ValueError):
    pass


class InvalidCredentialsError(ValueError):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_registration(name: object, email: object, password: object) -> tuple[str, str, str]:
    if not isinstance(name, str) or not name.strip():
        raise ValidationError("name is required")
    if not isinstance(email, str) or not EMAIL_PATTERN.match(normalize_email(email)):
        raise ValidationError("a valid email is required")
    if not isinstance(password, str) or len(password) < 8:
        raise ValidationError("password must be at least 8 characters")
    return name.strip(), normalize_email(email), password


class AuthService:
    def __init__(self, repository):
        self.repository = repository

    def register(self, name: object, email: object, password: object):
        name, email, password = validate_registration(name, email, password)
        if self.repository.find_by_email(email) is not None:
            raise DuplicateEmailError("registration could not be completed")
        return self.repository.create(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            registration_date=datetime.now(timezone.utc).replace(tzinfo=None),
        )

    def authenticate(self, email: object, password: object):
        if not isinstance(email, str) or not isinstance(password, str):
            raise InvalidCredentialsError("invalid credentials")
        student = self.repository.find_by_email(normalize_email(email))
        if student is None or not check_password_hash(student.password, password):
            raise InvalidCredentialsError("invalid credentials")
        return student

    def get_profile(self, student_id: int):
        return self.repository.get(student_id)

    def update_profile(self, student_id: int, name: object, email: object):
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("name is required")
        if not isinstance(email, str) or not EMAIL_PATTERN.match(normalize_email(email)):
            raise ValidationError("a valid email is required")
        normalized_email = normalize_email(email)
        existing = self.repository.find_by_email(normalized_email)
        if existing is not None and existing.student_id != student_id:
            raise DuplicateEmailError("profile could not be updated")
        return self.repository.update_profile(student_id, name.strip(), normalized_email)