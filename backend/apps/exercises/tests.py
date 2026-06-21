"""Phase 4 exercise-engine tests (master prompt §14.4: attempt is critical)."""
import pytest
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APIClient

from apps.exercises.correctors import get_corrector
from apps.exercises.models import Exercise, ExerciseAttempt
from apps.users.models import User


@pytest.fixture
def seeded(db):
    call_command("seed")


@pytest.fixture
def auth_client(seeded):
    client = APIClient()
    user = User.objects.create_user(email="e@test.com", password="pass12345")
    client.force_authenticate(user)
    return client, user


def _ex(code):
    return Exercise.objects.get(template__code=code)


# --- corrector unit tests -------------------------------------------------- #
@pytest.mark.django_db
def test_multiple_choice_corrector(seeded):
    c = get_corrector("multiple_choice")
    content = {"options": ["a", "b"], "correct_index": 1}
    assert c.check(content, {"selected_index": 1}) == (True, 1.0)
    assert c.check(content, {"selected_index": 0}) == (False, 0.0)


@pytest.mark.django_db
def test_fill_blank_case_insensitive(seeded):
    c = get_corrector("fill_blank")
    assert c.check({"answer": "am"}, {"answer": "  AM "})[0] is True


@pytest.mark.django_db
def test_reorder_partial_credit(seeded):
    c = get_corrector("reorder")
    content = {"correct_order": ["I", "am", "a", "student"]}
    ok, frac = c.check(content, {"order": ["I", "am", "student", "a"]})
    assert ok is False
    assert 0 < frac < 1


@pytest.mark.django_db
def test_matching_corrector(seeded):
    c = get_corrector("matching")
    content = {"pairs": [{"left": "A", "right": "1"}, {"left": "B", "right": "2"}]}
    assert c.check(content, {"pairs": content["pairs"]}) == (True, 1.0)


@pytest.mark.django_db
def test_final_test_aggregates(seeded):
    ex = _ex("final_test")
    ids = ex.content["exercise_ids"]
    # Build a fully-correct answer set from each sub-exercise's content.
    answers = {}
    for sub in Exercise.objects.filter(id__in=ids).select_related("template"):
        code = sub.template.code
        if code in ("multiple_choice", "listening"):
            answers[str(sub.id)] = {"selected_index": sub.content["correct_index"]}
        elif code == "true_false":
            answers[str(sub.id)] = {"answer": sub.content["answer"]}
        elif code == "fill_blank":
            answers[str(sub.id)] = {"answer": sub.content["answer"]}
        elif code == "matching":
            answers[str(sub.id)] = {"pairs": sub.content["pairs"]}
        elif code == "reorder":
            answers[str(sub.id)] = {"order": sub.content["correct_order"]}
        elif code == "pronunciation":
            answers[str(sub.id)] = {"transcript": sub.content["target_text"]}
    ok, frac = get_corrector("final_test").check(ex.content, {"answers": answers})
    assert ok is True and frac == 1.0


# --- attempt endpoint ------------------------------------------------------ #
def test_attempt_correct(auth_client):
    client, user = auth_client
    ex = _ex("multiple_choice")
    resp = client.post(
        reverse("v1:exercise-attempt", args=[ex.id]),
        {"answer": {"selected_index": ex.content["correct_index"]}},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["is_correct"] is True
    assert resp.data["score"] == ex.points
    assert ExerciseAttempt.objects.filter(user=user, exercise=ex).exists()


def test_attempt_incorrect_records_attempt(auth_client):
    client, user = auth_client
    ex = _ex("true_false")
    resp = client.post(
        reverse("v1:exercise-attempt", args=[ex.id]),
        {"answer": {"answer": not ex.content["answer"]}},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["is_correct"] is False
    assert resp.data["score"] == 0


def test_attempt_requires_auth(seeded):
    ex = _ex("multiple_choice")
    resp = APIClient().post(
        reverse("v1:exercise-attempt", args=[ex.id]),
        {"answer": {"selected_index": 0}},
        format="json",
    )
    assert resp.status_code == 401
