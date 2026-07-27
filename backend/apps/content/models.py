"""Content hierarchy (master prompt §6, §8).

Level → Unit → Lesson → LessonComponent[] (ordered, flexible).
Each component carries exactly one of: Video / VocabularyItem(s) / TextBlock /
Exercise(s). There is no fixed lesson template.
"""
from django.db import models

from apps.common.models import BaseModel


class Level(BaseModel):
    """A CEFR level (A1..C1)."""

    class Code(models.TextChoices):
        A1 = "A1", "A1"
        A2 = "A2", "A2"
        B1 = "B1", "B1"
        B2 = "B2", "B2"
        C1 = "C1", "C1"
        C2 = "C2", "C2"  # owner-approved extension (master prompt §12: six levels)

    code = models.CharField(max_length=2, choices=Code.choices, unique=True)
    name = models.CharField(max_length=100)          # e.g. "Survival" (no code prefix)
    name_fr = models.CharField(max_length=100, blank=True)  # e.g. "Survie"
    order = models.PositiveIntegerField(default=0)
    is_free = models.BooleanField(default=False)

    class Meta:
        db_table = "levels"
        ordering = ["order"]

    def __str__(self):
        return self.name


class Unit(BaseModel):
    level = models.ForeignKey(
        Level, on_delete=models.CASCADE, related_name="units"
    )
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "units"
        ordering = ["level", "order"]

    def __str__(self):
        return f"{self.level.code} · {self.title}"


class Lesson(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft (pending review)"
        PUBLISHED = "published", "Published"
        REJECTED = "rejected", "Rejected"

    unit = models.ForeignKey(
        Unit, on_delete=models.CASCADE, related_name="lessons"
    )
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    # v2 §5: API-imported content lands as `draft` until an admin approves it
    # in the review queue. Existing/manual content defaults to published.
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PUBLISHED
    )

    class Meta:
        db_table = "lessons"
        ordering = ["unit", "order"]

    def __str__(self):
        return self.title


class LessonComponent(BaseModel):
    """The flexible backbone: an ordered piece of a lesson."""

    class Type(models.TextChoices):
        VIDEO = "video", "Video"
        VOCABULARY = "vocabulary", "Vocabulary"
        TEXT = "text", "Text"
        EXERCISE = "exercise", "Exercise"

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="components"
    )
    type = models.CharField(max_length=20, choices=Type.choices)
    order = models.PositiveIntegerField(default=0)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "lesson_components"
        ordering = ["lesson", "order"]

    def __str__(self):
        return f"{self.lesson.title} · {self.type} #{self.order}"


class Video(BaseModel):
    """Video content. Hosting is isolated via storage_key (master prompt §7)."""

    class Status(models.TextChoices):
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"

    component = models.OneToOneField(
        LessonComponent, on_delete=models.CASCADE, related_name="video"
    )
    title = models.CharField(max_length=255, blank=True)
    duration = models.PositiveIntegerField(default=0, help_text="seconds")
    storage_key = models.CharField(max_length=512)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PROCESSING
    )
    # Optional timed transcript: {"segments": [{"start", "end",
    # "narration_en", "subtitle_ar"}, ...]} — powers in-player subtitles.
    script = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "videos"

    def __str__(self):
        return self.title or self.storage_key


class VocabularyItem(BaseModel):
    component = models.ForeignKey(
        LessonComponent, on_delete=models.CASCADE, related_name="vocabulary_items"
    )
    word = models.CharField(max_length=255)
    translation = models.CharField(max_length=255)
    audio_url = models.URLField(blank=True)
    image_url = models.URLField(blank=True)
    example_sentence = models.TextField(blank=True)
    # Pronunciation-training aids (optional; used by the mic exercise).
    syllables = models.CharField(max_length=100, blank=True)
    pronunciation_tip_ar = models.TextField(blank=True)
    difficulty = models.CharField(max_length=10, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "vocabulary_items"
        ordering = ["component", "order"]

    def __str__(self):
        return f"{self.word} → {self.translation}"


class TextBlock(BaseModel):
    component = models.OneToOneField(
        LessonComponent, on_delete=models.CASCADE, related_name="text_block"
    )
    content = models.TextField(help_text="markdown / rich text")

    class Meta:
        db_table = "text_blocks"

    def __str__(self):
        return f"TextBlock for {self.component_id}"


# --------------------------------------------------------------------------- #
# Selective translation (v2 §1.1)
# --------------------------------------------------------------------------- #
class WordLevel(BaseModel):
    """Static CEFR word classification lookup (Oxford-3000/5000-style list).

    Loaded via `manage.py load_wordlist`. A word is translated in a lesson
    only when its level here is ABOVE the lesson's own level."""

    word = models.CharField(max_length=100, unique=True, db_index=True)
    cefr_level = models.CharField(max_length=2)
    translation_ar = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "word_levels"
        ordering = ["word"]

    def __str__(self):
        return f"{self.word} ({self.cefr_level})"


class WordAnnotation(BaseModel):
    """A tappable word/phrase in a lesson with its Arabic translation.

    Produced by the reprocessing script (`annotate_lessons`). Only annotated
    words render as tappable in the app; everything else is plain text —
    never always-visible inline translations (v2 §1.1)."""

    class Kind(models.TextChoices):
        AUTO = "auto", "Automatic (above lesson level)"
        IDIOM = "idiom", "Idiom / fixed expression"
        MULTI_MEANING = "multi_meaning", "Multi-meaning (context-specific)"
        TARGET_VOCAB = "target_vocab", "Lesson target vocabulary"

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="word_annotations"
    )
    word = models.CharField(max_length=255, db_index=True)
    cefr_level = models.CharField(max_length=2, blank=True)
    translation_ar = models.CharField(max_length=255, blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.AUTO)
    # Ambiguous cases (idioms, multi-meaning, missing translation) that still
    # need an LLM/human pass before they're final.
    needs_review = models.BooleanField(default=False)

    class Meta:
        db_table = "word_annotations"
        unique_together = [("lesson", "word")]
        ordering = ["lesson", "word"]

    def __str__(self):
        return f"{self.lesson_id} · {self.word} ({self.kind})"
