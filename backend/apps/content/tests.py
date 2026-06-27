"""Phase 3 content API tests."""
import pytest
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APIClient

from apps.content.models import Lesson, Level, Unit
from apps.users.models import User


@pytest.fixture
def seeded(db):
    call_command("seed")


@pytest.fixture
def auth_client(seeded):
    client = APIClient()
    user = User.objects.create_user(email="c@test.com", password="pass12345")
    client.force_authenticate(user)
    return client


def test_levels_require_auth():
    assert APIClient().get(reverse("v1:level-list")).status_code == 401


def test_list_levels(auth_client):
    resp = auth_client.get(reverse("v1:level-list"))
    assert resp.status_code == 200
    assert resp.data["count"] == 6


def test_level_units(auth_client):
    level = Level.objects.get(code="A1")
    resp = auth_client.get(reverse("v1:level-units", args=[level.id]))
    assert resp.status_code == 200
    assert resp.data["count"] >= 1


def test_unit_lessons(auth_client):
    unit = Unit.objects.first()
    resp = auth_client.get(reverse("v1:unit-lessons", args=[unit.id]))
    assert resp.status_code == 200
    assert resp.data["count"] >= 1


def test_lesson_detail_returns_ordered_components(auth_client):
    lesson = Lesson.objects.get(title="Checking in")
    resp = auth_client.get(reverse("v1:lesson-detail", args=[lesson.id]))
    assert resp.status_code == 200
    components = resp.data["components"]
    orders = [c["order"] for c in components]
    assert orders == sorted(orders)
    types = {c["type"] for c in components}
    assert {"text", "vocabulary", "video", "exercise"} <= types


def test_lesson_detail_hides_exercise_answers(auth_client):
    lesson = Lesson.objects.get(title="Checking in")
    resp = auth_client.get(reverse("v1:lesson-detail", args=[lesson.id]))
    for comp in resp.data["components"]:
        if comp["type"] != "exercise":
            continue
        for ex in comp["payload"]:
            assert "correct_index" not in ex["content"]
            assert "answer" not in ex["content"]
            assert "correct_order" not in ex["content"]


def test_video_payload_has_playback_url(auth_client):
    lesson = Lesson.objects.get(title="Checking in")
    resp = auth_client.get(reverse("v1:lesson-detail", args=[lesson.id]))
    video_comp = next(c for c in resp.data["components"] if c["type"] == "video")
    assert "playback_url" in video_comp["payload"]
    assert video_comp["payload"]["playback_url"].endswith(".m3u8")


def test_vocabulary_payload_has_image_url(auth_client):
    lesson = Lesson.objects.get(title="Checking in")
    resp = auth_client.get(reverse("v1:lesson-detail", args=[lesson.id]))
    vocab = next(c for c in resp.data["components"] if c["type"] == "vocabulary")
    assert vocab["payload"], "vocabulary should have items"
    for item in vocab["payload"]:
        assert "image_url" in item
    # Seeded items carry demo images.
    assert any(item["image_url"] for item in vocab["payload"])
