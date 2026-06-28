"""Phase 5 tests: progress, placement, certificates (critical path §14.4)."""
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.content.models import Lesson, Level, Unit
from apps.progress.models import Certificate, PlacementResult, Progress
from apps.progress.services import (
    compute_streak,
    lessons_overview,
    units_overview,
)
from apps.users.models import User


@pytest.fixture
def seeded(db):
    call_command("seed")


@pytest.fixture
def auth_client(seeded):
    client = APIClient()
    user = User.objects.create_user(email="p@test.com", password="pass12345")
    client.force_authenticate(user)
    return client, user


# --- Placement ------------------------------------------------------------- #
def test_placement_test_hides_answers(auth_client):
    client, _ = auth_client
    resp = client.get(reverse("v1:placement-test"))
    assert resp.status_code == 200
    for q in resp.data["questions"]:
        assert "correct_index" not in q


def test_placement_submit_assigns_level(auth_client):
    client, user = auth_client
    # All wrong -> A1
    resp = client.post(
        reverse("v1:placement-submit"),
        {"answers": {"q1": 9, "q2": 9}},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["assigned_level"]["code"] == "A1"
    assert PlacementResult.objects.filter(user=user).exists()


def test_placement_high_score_high_level(auth_client):
    client, _ = auth_client
    from apps.progress import placement

    answers = {q["id"]: q["correct_index"] for q in placement.QUESTIONS}
    resp = client.post(
        reverse("v1:placement-submit"), {"answers": answers}, format="json"
    )
    assert resp.data["assigned_level"]["code"] == "C2"


# --- Progress -------------------------------------------------------------- #
def test_progress_overview_shape(auth_client):
    client, _ = auth_client
    resp = client.get(reverse("v1:progress-overview"))
    assert resp.status_code == 200
    assert len(resp.data["levels"]) == 6
    first = resp.data["levels"][0]
    assert {"percent", "completed_lessons", "total_lessons", "points", "locked"} <= set(first)


def test_progress_overview_has_summary(auth_client):
    client, _ = auth_client
    resp = client.get(reverse("v1:progress-overview"))
    summary = resp.data["summary"]
    assert {"xp", "streak", "completed_lessons", "current_level", "continue"} <= set(
        summary
    )
    assert summary["current_level"]["code"]  # a level is always suggested


# --- Sequential lock + gamification --------------------------------------- #
@pytest.fixture
def ladder(db):
    """A level with one unit and three ordered lessons."""
    level = Level.objects.create(code="ZZ", name="Test", order=99, is_free=True)
    unit = Unit.objects.create(level=level, title="U1", order=1)
    lessons = [
        Lesson.objects.create(unit=unit, title=f"L{i}", order=i)
        for i in range(1, 4)
    ]
    return level, unit, lessons


def test_lessons_overview_sequential_lock(ladder):
    level, unit, lessons = ladder
    user = User.objects.create_user(email="l@test.com", password="pass12345")

    rows = lessons_overview(user, unit.id)
    assert rows[0]["locked"] is False
    assert rows[1]["locked"] is True and rows[2]["locked"] is True

    Progress.objects.create(
        user=user,
        lesson=lessons[0],
        status=Progress.Status.COMPLETED,
        completed_at=timezone.now(),
    )
    rows = lessons_overview(user, unit.id)
    assert rows[0]["percent"] == 100
    assert rows[1]["locked"] is False  # next unlocks
    assert rows[2]["locked"] is True


def test_units_overview_sequential_lock(ladder):
    level, unit, lessons = ladder
    user = User.objects.create_user(email="u@test.com", password="pass12345")
    unit2 = Unit.objects.create(level=level, title="U2", order=2)
    Lesson.objects.create(unit=unit2, title="L1", order=1)

    rows = units_overview(user, level.id)
    assert rows[0]["locked"] is False and rows[1]["locked"] is True

    for lesson in lessons:  # finish unit 1
        Progress.objects.create(
            user=user,
            lesson=lesson,
            status=Progress.Status.COMPLETED,
            completed_at=timezone.now(),
        )
    rows = units_overview(user, level.id)
    assert rows[0]["is_completed"] is True
    assert rows[1]["locked"] is False


def test_compute_streak(ladder):
    _, _, lessons = ladder
    user = User.objects.create_user(email="s@test.com", password="pass12345")
    now = timezone.now()
    Progress.objects.create(
        user=user, lesson=lessons[0],
        status=Progress.Status.COMPLETED, completed_at=now,
    )
    Progress.objects.create(
        user=user, lesson=lessons[1],
        status=Progress.Status.COMPLETED, completed_at=now - timedelta(days=1),
    )
    assert compute_streak(user) == 2
    # A 3-day-old completion is not consecutive -> streak stays 2.
    Progress.objects.create(
        user=user, lesson=lessons[2],
        status=Progress.Status.COMPLETED, completed_at=now - timedelta(days=3),
    )
    assert compute_streak(user) == 2


def test_update_lesson_progress(auth_client):
    client, user = auth_client
    lesson = Lesson.objects.get(title="Checking in")
    resp = client.post(
        reverse("v1:progress-lesson", args=[lesson.id]),
        {"status": "completed", "score": 10, "time_spent": 300},
        format="json",
    )
    assert resp.status_code == 200
    prog = Progress.objects.get(user=user, lesson=lesson)
    assert prog.status == "completed"
    assert prog.completed_at is not None


# --- Certificates ---------------------------------------------------------- #
def test_certificate_issued_on_level_completion(auth_client):
    client, user = auth_client
    level = Level.objects.get(code="A1")
    lessons = Lesson.objects.filter(unit__level=level)
    last_resp = None
    for lesson in lessons:
        last_resp = client.post(
            reverse("v1:progress-lesson", args=[lesson.id]),
            {"status": "completed"},
            format="json",
        )
    assert last_resp.data["certificate_issued"] is True
    assert Certificate.objects.filter(user=user, level=level).exists()


def test_certificate_pdf_download(auth_client):
    client, user = auth_client
    level = Level.objects.get(code="A1")
    cert = Certificate.objects.create(
        user=user, level=level, certificate_number="CERT-A1-TEST1234"
    )
    resp = client.get(reverse("v1:certificate-pdf", args=[cert.id]))
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


def test_certificate_list_only_own(auth_client):
    client, user = auth_client
    other = User.objects.create_user(email="other@test.com", password="pass12345")
    level = Level.objects.get(code="A1")
    Certificate.objects.create(
        user=other, level=level, certificate_number="CERT-A1-OTHER999"
    )
    resp = client.get(reverse("v1:certificate-list"))
    assert resp.data["count"] == 0
