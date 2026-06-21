"""Exercise engine (master prompt §8, §9).

Exercises are template-driven JSON: adding a new template later means a new
ExerciseTemplate row + a corrector + a Flutter widget — never a DB change.
"""
from django.db import models

from apps.common.models import BaseModel


class ExerciseTemplate(BaseModel):
    """One of the eight built-in exercise templates (master prompt §9)."""

    class Code(models.TextChoices):
        MULTIPLE_CHOICE = "multiple_choice", "Multiple Choice"
        TRUE_FALSE = "true_false", "True / False"
        FILL_BLANK = "fill_blank", "Fill in the Blank"
        MATCHING = "matching", "Matching"
        REORDER = "reorder", "Reorder"
        LISTENING = "listening", "Listening"
        PRONUNCIATION = "pronunciation", "Pronunciation"
        FINAL_TEST = "final_test", "Final Test"

    code = models.CharField(max_length=30, choices=Code.choices, unique=True)
    name = models.CharField(max_length=100)
    content_schema = models.JSONField(
        default=dict, blank=True,
        help_text="Describes the accepted shape of Exercise.content",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "exercise_templates"
        ordering = ["code"]

    def __str__(self):
        return self.name


class Exercise(BaseModel):
    component = models.ForeignKey(
        "content.LessonComponent",
        on_delete=models.CASCADE,
        related_name="exercises",
    )
    template = models.ForeignKey(
        ExerciseTemplate, on_delete=models.PROTECT, related_name="exercises"
    )
    content = models.JSONField(help_text="Actual content, matching the template")
    points = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "exercises"
        ordering = ["component", "order"]

    def __str__(self):
        return f"{self.template.code} #{self.order}"


class ExerciseAttempt(BaseModel):
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="attempts"
    )
    exercise = models.ForeignKey(
        Exercise, on_delete=models.CASCADE, related_name="attempts"
    )
    answer = models.JSONField()
    is_correct = models.BooleanField(default=False)
    score = models.IntegerField(default=0)
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "exercise_attempts"
        ordering = ["-attempted_at"]

    def __str__(self):
        return f"{self.user_id} · {self.exercise_id} · {self.is_correct}"
