"""Phase 5 tests: progress, placement, certificates (critical path §14.4)."""
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.content.models import Lesson, Level, Unit
from apps.progress.models import (
    Certificate,
    PlacementResult,
    Progress,
    UnitAssessment,
    VocabularyProgress,
)
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


def test_units_overview_mastery_gate(ladder):
    """Next unit unlocks only after lessons complete AND assessment passed."""
    level, unit, lessons = ladder
    user = User.objects.create_user(email="u@test.com", password="pass12345")
    unit2 = Unit.objects.create(level=level, title="U2", order=2)
    Lesson.objects.create(unit=unit2, title="L1", order=1)

    rows = units_overview(user, level.id)
    assert rows[0]["locked"] is False and rows[1]["locked"] is True

    for lesson in lessons:  # finish unit 1's lessons
        Progress.objects.create(
            user=user,
            lesson=lesson,
            status=Progress.Status.COMPLETED,
            completed_at=timezone.now(),
        )
    rows = units_overview(user, level.id)
    assert rows[0]["is_completed"] is True
    assert rows[0]["assessment_ready"] is True
    assert rows[1]["locked"] is True  # still gated by the assessment

    UnitAssessment.objects.create(
        user=user, unit=unit, score=9, max_score=10, passed=True
    )
    rows = units_overview(user, level.id)
    assert rows[0]["assessment_passed"] is True
    assert rows[1]["locked"] is False  # mastery unlocks the next unit


# --- Unit assessment -------------------------------------------------------- #
def _correct_answer_for(exercise):
    c, code = exercise.content, exercise.template.code
    if code in ("multiple_choice", "listening"):
        return {"selected_index": c["correct_index"]}
    if code == "true_false":
        return {"answer": c["answer"]}
    if code == "fill_blank":
        return {"answer": c["answer"]}
    if code == "matching":
        return {"pairs": c["pairs"]}
    if code == "reorder":
        return {"order": c["correct_order"]}
    return {}


def test_unit_assessment_generate_sanitized(auth_client):
    client, _ = auth_client
    unit = Unit.objects.first()
    resp = client.get(reverse("v1:unit-assessment", args=[unit.id]))
    assert resp.status_code == 200
    questions = resp.data["questions"]
    assert questions
    for q in questions:
        assert "correct_index" not in q["content"]
        assert "answer" not in q["content"]
        assert q["template_code"] not in ("pronunciation", "final_test")


def test_unit_assessment_fail_and_pass(auth_client):
    from apps.exercises.models import Exercise

    client, user = auth_client
    unit = Unit.objects.first()
    resp = client.get(reverse("v1:unit-assessment", args=[unit.id]))
    questions = resp.data["questions"]
    exercises = {
        str(e.id): e
        for e in Exercise.objects.filter(
            component__lesson__unit=unit
        ).select_related("template")
    }

    # All wrong -> failed attempt #1
    wrong = {q["id"]: {"selected_index": 99} for q in questions}
    resp = client.post(
        reverse("v1:unit-assessment", args=[unit.id]),
        {"answers": wrong},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["passed"] is False and resp.data["attempt"] == 1

    # All correct -> passed attempt #2
    right = {q["id"]: _correct_answer_for(exercises[q["id"]]) for q in questions}
    resp = client.post(
        reverse("v1:unit-assessment", args=[unit.id]),
        {"answers": right},
        format="json",
    )
    assert resp.data["passed"] is True and resp.data["attempt"] == 2
    assert UnitAssessment.objects.filter(user=user, unit=unit).count() == 2


def test_unit_rating(auth_client):
    client, user = auth_client
    unit = Unit.objects.first()
    resp = client.post(
        reverse("v1:unit-rating", args=[unit.id]), {"rating": "up"}, format="json"
    )
    assert resp.status_code == 200
    from apps.progress.models import ContentRating

    assert ContentRating.objects.get(user=user, unit=unit).rating == "up"


# --- Lesson phases ------------------------------------------------------------ #
def test_lesson_phase_marks_step_completed(auth_client):
    client, user = auth_client
    lesson = Lesson.objects.get(title="Checking in")
    resp = client.post(
        reverse("v1:progress-phase", args=[lesson.id]), {"phase": 2}, format="json"
    )
    assert resp.status_code == 200 and resp.data["phases"] == [2]

    rows = lessons_overview(user, lesson.unit_id)
    row = next(r for r in rows if r["id"] == str(lesson.id))
    vocab = next(s for s in row["steps"] if s["type"] == "vocabulary")
    assert vocab["completed"] is True
    others = [s for s in row["steps"] if s["type"] != "vocabulary"]
    assert all(not s["completed"] for s in others)
    # Touching a phase marks the lesson in progress.
    assert Progress.objects.get(user=user, lesson=lesson).status == "in_progress"


# --- Vocabulary tracking ------------------------------------------------------ #
def test_vocab_track_promotion(auth_client):
    from apps.content.models import VocabularyItem

    client, user = auth_client
    item = VocabularyItem.objects.first()
    url = reverse("v1:vocab-track")

    client.post(url, {"results": [{"item_id": str(item.id), "correct": True}]},
                format="json")
    vp = VocabularyProgress.objects.get(user=user, vocabulary_item=item)
    assert vp.status == "learned"

    for _ in range(2):
        client.post(url, {"results": [{"item_id": str(item.id), "correct": True}]},
                    format="json")
    vp.refresh_from_db()
    assert vp.status == "mastered" and vp.correct_count == 3

    other = VocabularyItem.objects.exclude(id=item.id).first()
    client.post(url, {"results": [{"item_id": str(other.id), "correct": False}]},
                format="json")
    assert (
        VocabularyProgress.objects.get(user=user, vocabulary_item=other).status
        == "seen"
    )


# --- Hints + answer reveal ---------------------------------------------------- #
def test_hint_and_attempt_reveal(auth_client):
    from apps.exercises.models import Exercise

    client, _ = auth_client
    ex = Exercise.objects.filter(template__code="multiple_choice").first()
    correct_text = ex.content["options"][ex.content["correct_index"]]

    r1 = client.post(
        reverse("v1:exercise-hint", args=[ex.id]), {"level": 1}, format="json"
    )
    assert r1.status_code == 200
    assert ex.content["correct_index"] not in r1.data.get("eliminate", [])

    r2 = client.post(
        reverse("v1:exercise-hint", args=[ex.id]), {"level": 2}, format="json"
    )
    assert r2.data["hint"] == correct_text

    # Correct with a hint -> half points.
    r3 = client.post(
        reverse("v1:exercise-attempt", args=[ex.id]),
        {"answer": {"selected_index": ex.content["correct_index"]},
         "used_hint": True},
        format="json",
    )
    assert r3.data["is_correct"] is True
    assert r3.data["score"] == round(ex.points * 0.5)

    # Wrong answer reveals the correction.
    r4 = client.post(
        reverse("v1:exercise-attempt", args=[ex.id]),
        {"answer": {"selected_index": 99}},
        format="json",
    )
    assert r4.data["is_correct"] is False
    assert r4.data["correct_answer"] == correct_text


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


def _pdf_page_text(pdf_bytes: bytes) -> str:
    """Inflate the (single) Flate content stream of our generated PDF."""
    import zlib

    start = pdf_bytes.index(b"stream\n") + len(b"stream\n")
    end = pdf_bytes.index(b"\nendstream", start)
    return zlib.decompress(pdf_bytes[start:end]).decode("latin-1")


def test_certificate_pdf_renders_details(auth_client):
    client, user = auth_client
    user.full_name = "Yasser Abdelaziz"
    user.save()
    level = Level.objects.get(code="A1")
    cert = Certificate.objects.create(
        user=user, level=level, certificate_number="CERT-A1-TEST5678"
    )
    resp = client.get(reverse("v1:certificate-pdf", args=[cert.id]))
    text = _pdf_page_text(resp.content)
    assert "Yasser Abdelaziz" in text
    assert "CERTIFICATE" in text
    assert "LEVEL A1" in text
    assert "CERT-A1-TEST5678" in text


def test_certificate_pdf_arabic_name_falls_back_to_email(auth_client):
    # The standard PDF fonts can't render Arabic script; the renderer must
    # fall back to the email handle instead of emitting broken glyphs.
    client, user = auth_client
    user.full_name = "ياسر عبد العزيز"
    user.save()
    level = Level.objects.get(code="A1")
    cert = Certificate.objects.create(
        user=user, level=level, certificate_number="CERT-A1-TEST9999"
    )
    resp = client.get(reverse("v1:certificate-pdf", args=[cert.id]))
    assert resp.status_code == 200
    text = _pdf_page_text(resp.content)
    assert user.email.split("@")[0] in text


def test_certificate_list_only_own(auth_client):
    client, user = auth_client
    other = User.objects.create_user(email="other@test.com", password="pass12345")
    level = Level.objects.get(code="A1")
    Certificate.objects.create(
        user=other, level=level, certificate_number="CERT-A1-OTHER999"
    )
    resp = client.get(reverse("v1:certificate-list"))
    assert resp.data["count"] == 0


# --- Advanced stats dashboard (UX prompt 2.2) ------------------------------- #
def _practice(user, accuracy_pairs):
    """Create exercise attempts: [(exercise, is_correct), ...]."""
    from apps.exercises.models import ExerciseAttempt

    for exercise, ok in accuracy_pairs:
        ExerciseAttempt.objects.create(
            user=user, exercise=exercise, answer={}, is_correct=ok,
            score=1 if ok else 0,
        )


def test_stats_overview_counts(auth_client):
    client, user = auth_client
    lesson = Lesson.objects.first()
    Progress.objects.create(
        user=user, lesson=lesson, status=Progress.Status.COMPLETED,
        time_spent=300, completed_at=timezone.now(),
    )
    from apps.content.models import VocabularyItem

    item = VocabularyItem.objects.first()
    VocabularyProgress.objects.create(
        user=user, vocabulary_item=item,
        status=VocabularyProgress.Status.MASTERED, correct_count=3,
    )
    resp = client.get(reverse("v1:stats-overview"))
    assert resp.status_code == 200
    assert resp.data["lessons_completed"] == 1
    assert resp.data["words_learned"] == 1
    assert resp.data["words_mastered"] == 1
    assert resp.data["total_time_seconds"] == 300
    assert 0 < resp.data["overall_percent"] <= 100


def test_vocabulary_heatmap_percent(auth_client):
    client, user = auth_client
    from apps.content.models import VocabularyItem

    item = VocabularyItem.objects.select_related(
        "component__lesson__unit"
    ).first()
    VocabularyProgress.objects.create(
        user=user, vocabulary_item=item,
        status=VocabularyProgress.Status.LEARNED, correct_count=1,
    )
    resp = client.get(reverse("v1:stats-vocab-heatmap"))
    assert resp.status_code == 200
    unit_id = str(item.component.lesson.unit_id)
    row = next(u for u in resp.data["units"] if u["unit_id"] == unit_id)
    assert row["learned_words"] == 1
    assert row["percent"] > 0
    assert row["status"] in ("strong", "growing", "weak")


def test_grammar_skills_and_weak_areas(auth_client):
    client, user = auth_client
    from apps.exercises.models import Exercise

    exercise = Exercise.objects.select_related(
        "component__lesson__unit"
    ).first()
    # 1 correct out of 4 -> weak area (accuracy 25%, >= 3 attempts).
    _practice(user, [(exercise, True), (exercise, False),
                     (exercise, False), (exercise, False)])

    resp = client.get(reverse("v1:stats-grammar-skills"))
    assert resp.status_code == 200
    skill = resp.data["skills"][0]
    assert skill["attempts"] == 4
    assert skill["accuracy"] == 25
    assert skill["status"] == "weak"

    resp = client.get(reverse("v1:stats-weak-areas"))
    areas = resp.data["areas"]
    assert len(areas) == 1
    assert areas[0]["accuracy"] == 25
    assert areas[0]["practice_lesson_id"]


def test_time_investment_buckets(auth_client):
    client, user = auth_client
    lesson = Lesson.objects.first()
    Progress.objects.create(
        user=user, lesson=lesson, status=Progress.Status.COMPLETED,
        time_spent=600, completed_at=timezone.now(),
    )
    resp = client.get(reverse("v1:stats-time-investment"))
    assert resp.status_code == 200
    assert len(resp.data["days"]) == 30
    assert len(resp.data["weeks"]) == 4
    assert resp.data["total_seconds"] == 600
    assert resp.data["days"][-1]["seconds"] == 600  # logged today


# --- Achievements + notification preferences (UX prompt 2.3 / 3.2) ---------- #
def test_achievements_unlock_first_lesson(auth_client):
    client, user = auth_client
    resp = client.get(reverse("v1:achievements-all"))
    assert resp.status_code == 200
    assert resp.data["newly_unlocked"] == []
    assert all(not b["unlocked"] for b in resp.data["badges"])

    Progress.objects.create(
        user=user,
        lesson=Lesson.objects.first(),
        status=Progress.Status.COMPLETED,
        completed_at=timezone.now(),
    )
    resp = client.get(reverse("v1:achievements-all"))
    assert "first_lesson" in resp.data["newly_unlocked"]
    badge = next(b for b in resp.data["badges"] if b["type"] == "first_lesson")
    assert badge["unlocked"] is True and badge["title_ar"]

    # Second call: still unlocked, no longer "new".
    resp = client.get(reverse("v1:achievements-all"))
    assert resp.data["newly_unlocked"] == []

    resp = client.get(reverse("v1:achievements"))
    assert [b["type"] for b in resp.data["badges"]] == ["first_lesson"]


def test_notification_preferences_roundtrip(auth_client):
    client, _ = auth_client
    resp = client.get(reverse("v1:notification-preferences"))
    assert resp.status_code == 200
    assert resp.data["streak_reminder"] is True
    assert resp.data["preferred_time"] == "08:00"

    resp = client.post(
        reverse("v1:notification-preferences"),
        {"streak_reminder": False, "preferred_time": "20:30"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["streak_reminder"] is False
    assert resp.data["preferred_time"] == "20:30"
    # unchanged flags keep their defaults
    assert resp.data["achievement_alert"] is True

    resp = client.post(
        reverse("v1:notification-preferences"),
        {"preferred_time": "bogus"},
        format="json",
    )
    assert resp.status_code == 400
