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


class UserAchievement(BaseModel):
    """An unlocked badge (UX prompt 3.2). The catalog and unlock rules live in
    achievements.py; rows are inserted when a rule is first satisfied."""

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="achievements"
    )
    achievement_type = models.CharField(max_length=50)
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_achievements"
        unique_together = [("user", "achievement_type")]
        ordering = ["-unlocked_at"]

    def __str__(self):
        return f"{self.user_id} · {self.achievement_type}"


class NotificationPreference(BaseModel):
    """Per-user smart-notification switches (UX prompt 2.3). The app reads
    these to schedule/cancel its local notifications."""

    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="notification_preference",
    )
    streak_reminder = models.BooleanField(default=True)
    content_alert = models.BooleanField(default=True)
    weak_area_alert = models.BooleanField(default=True)
    achievement_alert = models.BooleanField(default=True)
    preferred_time = models.TimeField(default="08:00")

    class Meta:
        db_table = "notification_preferences"

    def __str__(self):
        return f"{self.user_id} @ {self.preferred_time}"
