"""Unit mastery assessment: 10 random questions from the unit's exercises,
graded server-side; pass >= 80% unlocks the next unit."""
import math
import random

from apps.exercises.correctors import get_corrector
from apps.exercises.models import Exercise
from apps.exercises.serializers import ExerciseSerializer

from .models import UnitAssessment

ASSESSMENT_SIZE = 10
PASS_RATIO = 0.8

# Templates that don't fit a timed written test.
_EXCLUDED = ("pronunciation", "final_test")


def build_questions(unit):
    """Pick up to ASSESSMENT_SIZE random exercises and return them sanitized
    (answers stripped by ExerciseSerializer, ids kept for grading)."""
    exercises = list(
        Exercise.objects.filter(component__lesson__unit=unit)
        .exclude(template__code__in=_EXCLUDED)
        .select_related("template")
        .prefetch_related("component__lesson")
    )
    random.shuffle(exercises)
    picked = exercises[:ASSESSMENT_SIZE]
    return ExerciseSerializer(picked, many=True).data


def grade(user, unit, answers: dict) -> UnitAssessment:
    """Grade {exercise_id: answer} strictly against this unit's exercises."""
    exercises = {
        str(e.id): e
        for e in Exercise.objects.filter(
            id__in=list(answers.keys()), component__lesson__unit=unit
        ).select_related("template")
    }
    total = max(len(answers), 1)
    correct = 0
    for ex_id, answer in answers.items():
        exercise = exercises.get(str(ex_id))
        if exercise is None:
            continue
        corrector = get_corrector(exercise.template.code)
        is_correct, _ = corrector.check(exercise.content, answer or {})
        if is_correct:
            correct += 1

    passed = correct >= math.ceil(PASS_RATIO * total)
    attempt = (
        UnitAssessment.objects.filter(user=user, unit=unit).count() + 1
    )
    return UnitAssessment.objects.create(
        user=user,
        unit=unit,
        score=correct,
        max_score=total,
        passed=passed,
        attempt=attempt,
    )
