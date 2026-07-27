"""Admin panel + import API tests (v2 §4/§5): RBAC, trust tiers, review flow."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.content.models import Lesson, Level, Unit
from apps.exercises.models import ExerciseTemplate
from apps.users.models import User

from .models import AdminUser, APIKey, ImportLog


@pytest.fixture
def level(db):
    return Level.objects.create(code="A1", name="Breakthrough", order=1)


def make_admin(role, email):
    admin = AdminUser(email=email, role=role)
    admin.set_password("panelpass123")
    admin.save()
    return admin


def login(client, email):
    resp = client.post(
        reverse("v1:adminpanel:admin-login"),
        {"email": email, "password": "panelpass123"},
        format="json",
    )
    assert resp.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['token']}")
    return resp.data


@pytest.fixture
def super_client(db):
    make_admin(AdminUser.Role.SUPER, "super@panel.test")
    c = APIClient()
    login(c, "super@panel.test")
    return c


@pytest.fixture
def content_client(db):
    make_admin(AdminUser.Role.CONTENT, "content@panel.test")
    c = APIClient()
    login(c, "content@panel.test")
    return c


@pytest.fixture
def support_client(db):
    make_admin(AdminUser.Role.SUPPORT, "support@panel.test")
    c = APIClient()
    login(c, "support@panel.test")
    return c


# --------------------------------------------------------------------------- #
# RBAC (§4.2) — enforced in the backend, not just hidden UI
# --------------------------------------------------------------------------- #
def test_login_bad_password_rejected(db):
    make_admin(AdminUser.Role.SUPER, "s@panel.test")
    resp = APIClient().post(
        reverse("v1:adminpanel:admin-login"),
        {"email": "s@panel.test", "password": "wrong"},
        format="json",
    )
    assert resp.status_code == 401


def test_end_user_jwt_cannot_access_admin_api(db):
    user = User.objects.create_user(email="u@test.com", password="pass12345")
    client = APIClient()
    client.force_authenticate(user)
    assert client.get(reverse("v1:adminpanel:admin-stats")).status_code == 403


def test_content_admin_cannot_touch_users(content_client):
    assert content_client.get(
        reverse("v1:adminpanel:admin-users")
    ).status_code == 403
    assert content_client.post(
        reverse("v1:adminpanel:admin-premium-activate"), {}, format="json"
    ).status_code == 403


def test_support_admin_cannot_touch_content(support_client):
    assert support_client.get(
        reverse("v1:adminpanel:admin-content-tree")
    ).status_code == 403
    assert support_client.get(
        reverse("v1:adminpanel:admin-review-articles")
    ).status_code == 403


def test_only_super_manages_admins_and_keys(content_client, support_client):
    for client in (content_client, support_client):
        assert client.get(
            reverse("v1:adminpanel:admin-admins")
        ).status_code == 403
        assert client.get(
            reverse("v1:adminpanel:admin-api-keys")
        ).status_code == 403


def test_manual_premium_activation(support_client, db):
    user = User.objects.create_user(email="pay@test.com", password="pass12345")
    resp = support_client.post(
        reverse("v1:adminpanel:admin-premium-activate"),
        {"email": "pay@test.com", "plan_type": "monthly", "duration_days": 30},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["user"]["premium_active"] is True
    from apps.billing.models import PremiumGrant

    grant = PremiumGrant.objects.get(user=user)
    assert grant.source == PremiumGrant.Source.MANUAL_ADMIN


# --------------------------------------------------------------------------- #
# Content Import API (§5.1) — trust tiers + logging + review queue
# --------------------------------------------------------------------------- #
def _seed_templates():
    for code in ("multiple_choice", "true_false"):
        ExerciseTemplate.objects.get_or_create(code=code, defaults={"name": code})


def _lesson_payload(**overrides):
    payload = {
        "level": "A1",
        "unit": {"title": "Imported Unit", "order": 1},
        "lesson": {"title": "Imported Lesson", "order": 1},
        "components": [
            {"type": "text", "order": 1, "content": "# Hello"},
            {"type": "exercise", "order": 2, "exercises": [
                {"template": "multiple_choice",
                 "content": {"question": "?", "options": ["a", "b"],
                             "correct_index": 0}},
            ]},
        ],
    }
    payload.update(overrides)
    return payload


def make_key(trust):
    raw, prefix, key_hash = APIKey.generate()
    APIKey.objects.create(
        name=f"key-{trust}", prefix=prefix, key_hash=key_hash, trust_level=trust
    )
    return raw


def test_import_requires_api_key(level):
    resp = APIClient().post(
        reverse("v1:content-lessons-import"), _lesson_payload(), format="json"
    )
    assert resp.status_code in (401, 403)


def test_import_defaults_to_draft_and_hides_from_students(level, db):
    _seed_templates()
    raw = make_key(APIKey.Trust.DRAFT_ONLY)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    resp = client.post(
        reverse("v1:content-lessons-import"), _lesson_payload(), format="json"
    )
    assert resp.status_code == 201
    assert resp.data["status"] == "draft"
    lesson = Lesson.objects.get(id=resp.data["lesson_id"])
    assert lesson.status == Lesson.Status.DRAFT

    # Draft is invisible to the student API until approved.
    student = User.objects.create_user(email="s2@test.com", password="pass12345")
    sc = APIClient()
    sc.force_authenticate(student)
    assert sc.get(
        reverse("v1:lesson-detail", args=[lesson.id])
    ).status_code == 404


def test_low_trust_key_cannot_publish_direct(level, db):
    _seed_templates()
    raw = make_key(APIKey.Trust.DRAFT_ONLY)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    resp = client.post(
        reverse("v1:content-lessons-import"),
        _lesson_payload(publish_mode="direct"),
        format="json",
    )
    assert resp.status_code == 403


def test_high_trust_key_publishes_direct_and_is_logged(level, db):
    _seed_templates()
    raw = make_key(APIKey.Trust.DIRECT_PUBLISH)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    resp = client.post(
        reverse("v1:content-lessons-import"),
        _lesson_payload(publish_mode="direct"),
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["status"] == "published"
    log = ImportLog.objects.get()
    assert log.publish_mode == "direct"
    assert log.content_id == resp.data["lesson_id"]  # traceability (§5.1)


def test_import_validates_schema(level, db):
    raw = make_key(APIKey.Trust.DRAFT_ONLY)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    resp = client.post(
        reverse("v1:content-lessons-import"),
        {"level": "Z9", "components": [{"type": "hologram"}]},
        format="json",
    )
    assert resp.status_code == 400
    assert any("Z9" in e for e in resp.data["errors"])
    assert any("hologram" in e for e in resp.data["errors"])


def test_review_queue_approve_flow(content_client, level, db):
    _seed_templates()
    raw = make_key(APIKey.Trust.DRAFT_ONLY)
    ic = APIClient()
    ic.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    lesson_id = ic.post(
        reverse("v1:content-lessons-import"), _lesson_payload(), format="json"
    ).data["lesson_id"]

    queue = content_client.get(reverse("v1:adminpanel:admin-review-lessons"))
    assert any(row["id"] == lesson_id for row in queue.data)

    resp = content_client.post(
        reverse("v1:adminpanel:admin-review-lesson-act",
                args=[lesson_id, "approve"])
    )
    assert resp.status_code == 200
    assert Lesson.objects.get(id=lesson_id).status == Lesson.Status.PUBLISHED
