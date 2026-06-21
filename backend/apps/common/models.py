"""Base models shared across apps.

Every table uses a UUID primary key (master prompt §3).
"""
import uuid

from django.db import models


class UUIDModel(models.Model):
    """Abstract base giving every model a UUID primary key."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """Abstract base adding created/updated timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimeStampedModel):
    """Convenience base: UUID pk + timestamps."""

    class Meta:
        abstract = True
