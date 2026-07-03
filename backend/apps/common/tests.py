"""Phase 1 smoke tests: data model + seed integrity."""
import pytest
from django.core.management import call_command

from apps.content.models import Lesson, LessonComponent, Level
from apps.exercises.models import Exercise, ExerciseTemplate
from apps.users.models import User


@pytest.fixture
def seeded(db):
    call_command("seed")


def test_seed_creates_six_levels(seeded):
    assert Level.objects.count() == 6
    assert set(Level.objects.values_list("code", flat=True)) == {
        "A1", "A2", "B1", "B2", "C1", "C2"
    }


def test_seed_creates_nine_templates(seeded):
    assert ExerciseTemplate.objects.count() == 9


def test_seed_creates_one_exercise_per_template(seeded):
    codes = set(ExerciseTemplate.objects.values_list("code", flat=True))
    used = set(
        Exercise.objects.values_list("template__code", flat=True)
    )
    # Every template appears in the sample lesson except dictation (it exists
    # for imported/authored content, not the seed demo).
    assert codes - used <= {"dictation"}


def test_seed_is_idempotent(seeded):
    call_command("seed")
    assert Level.objects.count() == 6
    assert ExerciseTemplate.objects.count() == 9


def test_sample_lesson_components_ordered(seeded):
    lesson = Lesson.objects.get(title="Checking in")
    orders = list(
        lesson.components.values_list("order", flat=True).order_by("order")
    )
    assert orders == sorted(orders)
    assert lesson.components.count() == 5


def test_uuid_primary_keys(seeded):
    level = Level.objects.first()
    assert isinstance(level.id.hex, str)  # UUID field


def test_demo_users_have_roles(seeded):
    assert User.objects.filter(role=User.Role.ADMIN).exists()
    assert User.objects.filter(role=User.Role.TEACHER).exists()
    assert User.objects.filter(role=User.Role.STUDENT).exists()
