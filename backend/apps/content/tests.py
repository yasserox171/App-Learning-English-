"""Phase 3 content API tests."""
import json

import pytest
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APIClient

from apps.content.models import Lesson, Level, Unit
from apps.exercises.models import Exercise
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
    # Enriched list: plain array with per-unit progress + lock state.
    assert len(resp.data) >= 1
    assert {"percent", "locked", "completed", "total"} <= set(resp.data[0])


def test_unit_lessons(auth_client):
    unit = Unit.objects.first()
    resp = auth_client.get(reverse("v1:unit-lessons", args=[unit.id]))
    assert resp.status_code == 200
    assert len(resp.data) >= 1
    assert {"status", "percent", "locked"} <= set(resp.data[0])
    assert resp.data[0]["locked"] is False  # first lesson always open


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


def test_import_content_creates_full_lesson(seeded, tmp_path):
    payload = [{
        "level": "A1",
        "unit": {"title": "Imported Unit", "order": 9},
        "lesson": {"title": "Imported Lesson", "order": 1},
        "components": [
            {"type": "text", "order": 1, "content": "hello"},
            {"type": "vocabulary", "order": 2, "items": [
                {"word": "Sea", "translation": "بحر",
                 "image_url": "imgs/sea.png", "order": 1},
            ]},
            {"type": "exercise", "order": 3, "exercises": [
                {"template": "multiple_choice", "points": 2, "order": 1,
                 "content": {"question": "?", "options": ["a", "b"],
                             "correct_index": 1}},
            ]},
        ],
    }]
    f = tmp_path / "lesson.json"
    f.write_text(json.dumps(payload), encoding="utf-8")

    call_command("import_content", str(f),
                 "--media-base-url", "http://x/media", "--media-dest", "d")

    lesson = Lesson.objects.get(title="Imported Lesson")
    assert lesson.unit.title == "Imported Unit"
    assert lesson.components.count() == 3
    # Relative media path was rewritten to an absolute URL.
    vocab = lesson.components.get(type="vocabulary").vocabulary_items.first()
    assert vocab.image_url == "http://x/media/d/imgs/sea.png"
    ex = Exercise.objects.get(component__lesson=lesson)
    assert ex.points == 2


def test_import_content_replace_clears_components(seeded, tmp_path):
    payload = {
        "level": "A1",
        "unit": {"title": "Rep Unit"},
        "lesson": {"title": "Rep Lesson"},
        "components": [{"type": "text", "order": 1, "content": "v1"}],
    }
    f = tmp_path / "l.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    call_command("import_content", str(f))
    call_command("import_content", str(f), "--replace")
    lesson = Lesson.objects.get(title="Rep Lesson")
    # --replace prevents duplicate components.
    assert lesson.components.count() == 1


def test_vocabulary_payload_has_image_url(auth_client):
    lesson = Lesson.objects.get(title="Checking in")
    resp = auth_client.get(reverse("v1:lesson-detail", args=[lesson.id]))
    vocab = next(c for c in resp.data["components"] if c["type"] == "vocabulary")
    assert vocab["payload"], "vocabulary should have items"
    for item in vocab["payload"]:
        assert "image_url" in item
    # Seeded items carry demo images.
    assert any(item["image_url"] for item in vocab["payload"])
