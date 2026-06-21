"""Phase 2 auth tests (master prompt §14.4: auth is a critical path)."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.models import User


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def student(db):
    return User.objects.create_user(
        email="s@test.com", password="pass12345", full_name="S"
    )


def test_register_returns_tokens(client, db):
    resp = client.post(
        reverse("v1:register"),
        {"email": "new@test.com", "password": "pass12345", "full_name": "New"},
        format="json",
    )
    assert resp.status_code == 201
    assert "access" in resp.data and "refresh" in resp.data
    assert resp.data["user"]["role"] == "student"


def test_register_forces_student_role(client, db):
    client.post(
        reverse("v1:register"),
        {"email": "x@test.com", "password": "pass12345", "role": "admin"},
        format="json",
    )
    assert User.objects.get(email="x@test.com").role == "student"


def test_login_returns_user_and_tokens(client, student):
    resp = client.post(
        reverse("v1:login"),
        {"email": "s@test.com", "password": "pass12345"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["user"]["email"] == "s@test.com"
    assert "access" in resp.data


def test_login_wrong_password(client, student):
    resp = client.post(
        reverse("v1:login"),
        {"email": "s@test.com", "password": "wrong"},
        format="json",
    )
    assert resp.status_code == 401


def test_me_requires_auth(client):
    assert client.get(reverse("v1:me")).status_code == 401


def test_me_returns_profile(client, student):
    client.force_authenticate(student)
    resp = client.get(reverse("v1:me"))
    assert resp.status_code == 200
    assert resp.data["email"] == "s@test.com"


def test_social_google_creates_user(client, db):
    resp = client.post(
        reverse("v1:social-google"),
        {"provider_uid": "g-123", "email": "g@test.com", "full_name": "G"},
        format="json",
    )
    assert resp.status_code == 200
    assert "access" in resp.data
    assert User.objects.filter(email="g@test.com").exists()


def test_social_google_reuses_user(client, db):
    payload = {"provider_uid": "g-9", "email": "g9@test.com"}
    client.post(reverse("v1:social-google"), payload, format="json")
    client.post(reverse("v1:social-google"), payload, format="json")
    assert User.objects.filter(email="g9@test.com").count() == 1
