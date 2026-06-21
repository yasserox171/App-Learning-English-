"""Phase 6 admin dashboard tests."""
import pytest
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from apps.users.models import User


@pytest.fixture
def seeded(db):
    call_command("seed")


@pytest.fixture
def admin_client(seeded):
    admin = User.objects.get(email="admin@lms.test")
    client = Client()
    client.force_login(admin)
    return client


def test_admin_index_shows_stats(admin_client):
    resp = admin_client.get(reverse("admin:index"))
    assert resp.status_code == 200
    assert resp.context["stats"]["levels"] == 6
    assert b"Platform statistics" in resp.content


def test_admin_lesson_changelist(admin_client):
    resp = admin_client.get(reverse("admin:content_lesson_changelist"))
    assert resp.status_code == 200


def test_admin_can_open_component_with_inlines(admin_client):
    from apps.content.models import LessonComponent

    comp = LessonComponent.objects.filter(type="exercise").first()
    resp = admin_client.get(
        reverse("admin:content_lessoncomponent_change", args=[comp.id])
    )
    assert resp.status_code == 200


def test_admin_requires_staff(seeded):
    student = User.objects.get(email="student@lms.test")
    client = Client()
    client.force_login(student)
    resp = client.get(reverse("admin:index"))
    # Non-staff are redirected to login.
    assert resp.status_code == 302
