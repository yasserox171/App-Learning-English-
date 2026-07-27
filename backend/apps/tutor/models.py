"""AI Tutor voice conversations (v2 §3).

A conversation sub-section within relevant lessons, themed to the lesson's
topic and vocabulary. Usage is capped by a SHARED daily limit across the whole
app (not per-lesson), configurable per tier (§3.5).
"""
from django.db import models

from apps.common.models import BaseModel


class AITutorSession(BaseModel):
    """One capped voice conversation (5-6 exchanges) tied to a lesson."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="tutor_sessions"
    )
    lesson = models.ForeignKey(
        "content.Lesson", on_delete=models.CASCADE, related_name="tutor_sessions"
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE
    )
    system_prompt = models.TextField(blank=True)
    # [{"role": "assistant"|"user", "text": ...}, ...] — full transcript.
    turns = models.JSONField(default=list)
    target_vocabulary = models.JSONField(default=list)
    # Progress measurement (§3.4): how many target terms the learner used.
    terms_used = models.PositiveIntegerField(default=0)
    terms_total = models.PositiveIntegerField(default=0)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ai_tutor_sessions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id} · {self.lesson_id} · {self.status}"


class AITutorUsage(BaseModel):
    """Per-user per-day session counter (v2 §3.5)."""

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="tutor_usage"
    )
    date = models.DateField()
    session_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "ai_tutor_usage"
        unique_together = [("user", "date")]

    def __str__(self):
        return f"{self.user_id} · {self.date} · {self.session_count}"
