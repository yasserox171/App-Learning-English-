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


# --- v2: guest accounts + conversion (§2.1) -------------------------------- #
def test_guest_account_created_without_input(client, db):
    from apps.news.models import Category

    Category.objects.create(code="general", name_en="General", is_default=True)
    resp = client.post(reverse("v1:guest"), {}, format="json")
    assert resp.status_code == 201
    assert resp.data["user"]["is_guest"] is True
    assert "access" in resp.data  # same JWT mechanism as registered users
    user = User.objects.get(id=resp.data["user"]["id"])
    assert user.interests.filter(code="general").exists()  # default interests


def test_guest_registration_converts_same_row(client, db):
    guest_resp = client.post(reverse("v1:guest"), {}, format="json")
    guest_id = guest_resp.data["user"]["id"]
    token = guest_resp.data["access"]

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    resp = client.post(
        reverse("v1:register"),
        {"email": "converted@test.com", "password": "pass12345",
         "full_name": "Converted"},
        format="json",
    )
    assert resp.status_code == 201
    # Same row, flipped in place — coins/progress survive automatically.
    assert resp.data["user"]["id"] == guest_id
    assert resp.data["user"]["is_guest"] is False
    user = User.objects.get(id=guest_id)
    assert user.email == "converted@test.com"
    assert user.check_password("pass12345")


def test_register_without_token_creates_new_user(client, db):
    resp = client.post(
        reverse("v1:register"),
        {"email": "plain@test.com", "password": "pass12345"},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["user"]["is_guest"] is False


# --- v2: Google Sign-In with server-side verification (§6.1) ---------------- #
def _mock_verify(monkeypatch, info):
    from apps.users import services

    monkeypatch.setattr(services, "verify_google_id_token", lambda tok: info)
    # views.py imports the module, so patching services is enough.


def test_google_login_creates_user(client, db, monkeypatch):
    _mock_verify(monkeypatch, {
        "sub": "g-123", "email": "g@test.com",
        "email_verified": True, "name": "G",
    })
    resp = client.post(
        reverse("v1:social-google"), {"id_token": "tok"}, format="json"
    )
    assert resp.status_code == 200
    assert User.objects.filter(email="g@test.com").exists()


def test_google_login_links_existing_email_only_if_verified(client, db,
                                                            monkeypatch):
    User.objects.create_user(email="linked@test.com", password="pass12345")
    _mock_verify(monkeypatch, {
        "sub": "g-77", "email": "linked@test.com",
        "email_verified": False, "name": "",
    })
    resp = client.post(
        reverse("v1:social-google"), {"id_token": "tok"}, format="json"
    )
    assert resp.status_code == 401  # unverified email cannot auto-link (§6.1)

    _mock_verify(monkeypatch, {
        "sub": "g-77", "email": "linked@test.com",
        "email_verified": True, "name": "",
    })
    resp = client.post(
        reverse("v1:social-google"), {"id_token": "tok"}, format="json"
    )
    assert resp.status_code == 200
    assert User.objects.filter(email="linked@test.com").count() == 1


def test_google_login_converts_guest(client, db, monkeypatch):
    guest_resp = client.post(reverse("v1:guest"), {}, format="json")
    guest_id = guest_resp.data["user"]["id"]

    _mock_verify(monkeypatch, {
        "sub": "g-55", "email": "guestgoogle@test.com",
        "email_verified": True, "name": "GG",
    })
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {guest_resp.data['access']}"
    )
    resp = client.post(
        reverse("v1:social-google"), {"id_token": "tok"}, format="json"
    )
    assert resp.status_code == 200
    assert resp.data["user"]["id"] == guest_id  # converted in place
    assert resp.data["user"]["is_guest"] is False


def test_google_login_reuses_social_link(client, db, monkeypatch):
    _mock_verify(monkeypatch, {
        "sub": "g-9", "email": "g9@test.com",
        "email_verified": True, "name": "",
    })
    client.post(reverse("v1:social-google"), {"id_token": "t"}, format="json")
    client.post(reverse("v1:social-google"), {"id_token": "t"}, format="json")
    assert User.objects.filter(email="g9@test.com").count() == 1
