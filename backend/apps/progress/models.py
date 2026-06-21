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
