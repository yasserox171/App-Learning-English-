"""Progress & assessment (master prompt §8).

Level progress is COMPUTED from Progress rows, never stored (master prompt §8).
"""
from django.db import models

from apps.common.models import BaseModel


class PlacementResult(BaseModel):
    """Outcome of the placement test that assigns a starting level."""

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="placement_results"
    )
    assigned_level = models.ForeignKey(
        "content.Level", on_delete=models.PROTECT, related_name="placements"
    )
    score = models.IntegerField(default=0)
    taken_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "placement_results"
        ordering = ["-taken_at"]

    def __str__(self):
        return f"{self.user_id} → {self.assigned_level_id}"


class Progress(BaseModel):
    """Per-lesson progress for a user."""

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="progress"
    )
    lesson = models.ForeignKey(
        "content.Lesson", on_delete=models.CASCADE, related_name="progress"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NOT_STARTED
    )
    score = models.IntegerField(default=0)
    time_spent = models.PositiveIntegerField(default=0, help_text="seconds")
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "progress"
        unique_together = [("user", "lesson")]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user_id} · {self.lesson_id} · {self.status}"


class LessonPhaseProgress(BaseModel):
    """A completed learning phase inside a lesson (micro-learning flow).

    Phases: 1=intro(text) 2=vocabulary 3=video 4=exercises 5=evaluation.
    A row's existence marks the phase as completed for that user."""

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="phase_progress"
    )
    lesson = models.ForeignKey(
        "content.Lesson", on_delete=models.CASCADE, related_name="phase_progress"
    )
    phase = models.PositiveSmallIntegerField()
    score = models.FloatField(default=0)
    completed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lesson_phase_progress"
        unique_together = [("user", "lesson", "phase")]
        ordering = ["lesson", "phase"]

    def __str__(self):
        return f"{self.user_id} · {self.lesson_id} · phase {self.phase}"


class UnitAssessment(BaseModel):
    """One attempt at a unit's mastery test (10 random questions, pass >= 80%)."""

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="unit_assessments"
    )
    unit = models.ForeignKey(
        "content.Unit", on_delete=models.CASCADE, related_name="assessments"
    )
    score = models.IntegerField(default=0)
    max_score = models.IntegerField(default=0)
    passed = models.BooleanField(default=False)
    attempt = models.PositiveIntegerField(default=1)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "unit_assessments"
        ordering = ["-completed_at"]

    def __str__(self):
        return f"{self.user_id} · {self.unit_id} · {self.score}/{self.max_score}"


class VocabularyProgress(BaseModel):
    """Per-word learning state: new -> seen -> learned -> mastered."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        SEEN = "seen", "Seen"
        LEARNED = "learned", "Learned"
        MASTERED = "mastered", "Mastered"

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="vocab_progress"
    )
    vocabulary_item = models.ForeignKey(
        "content.VocabularyItem",
        on_delete=models.CASCADE,
        related_name="progress",
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.NEW
    )
    correct_count = models.PositiveIntegerField(default=0)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vocabulary_progress"
        unique_together = [("user", "vocabulary_item")]

    def record(self, correct: bool):
        """Apply one quiz result and promote the status accordingly."""
        if correct:
            self.correct_count += 1
            self.status = (
                self.Status.MASTERED
                if self.correct_count >= 3
                else self.Status.LEARNED
            )
        elif self.status == self.Status.NEW:
            self.status = self.Status.SEEN
        self.save()

    def __str__(self):
        return f"{self.user_id} · {self.vocabulary_item_id} · {self.status}"


class ContentRating(BaseModel):
    """Thumbs up/down the learner gives a unit after passing its assessment."""

    class Rating(models.TextChoices):
        UP = "up", "Thumbs up"
        DOWN = "down", "Thumbs down"

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="content_ratings"
    )
    unit = models.ForeignKey(
        "content.Unit", on_delete=models.CASCADE, related_name="ratings"
    )
    rating = models.CharField(max_length=5, choices=Rating.choices)

    class Meta:
        db_table = "content_ratings"
        unique_together = [("user", "unit")]

    def __str__(self):
        return f"{self.user_id} · {self.unit_id} · {self.rating}"


class Certificate(BaseModel):
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="certificates"
    )
    level = models.ForeignKey(
        "content.Level", on_delete=models.PROTECT, related_name="certificates"
    )
    certificate_number = models.CharField(max_length=50, unique=True)
    pdf_url = models.URLField(blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "certificates"
        unique_together = [("user", "level")]
        ordering = ["-issued_at"]

    def __str__(self):
        return self.certificate_number
