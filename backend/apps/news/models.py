"""News & Stories models (v2 §2.2).

Two content types share one table: rewritten news articles (NewsAPI source,
always fully rewritten by an LLM — never verbatim) and original LLM-generated
stories. Content is personalized by category (user interests), CEFR level and
country, and goes through a draft → published review flow.
"""
from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel

NEWS_TTL_DAYS = 7


class Category(BaseModel):
    """A content/interest category (general, culture, sports, ...).

    ``is_default`` marks the starter set auto-assigned to new guest accounts
    (v2 §2.1 — no interest survey required)."""

    code = models.SlugField(unique=True)
    name_en = models.CharField(max_length=100)
    name_ar = models.CharField(max_length=100, blank=True)
    is_default = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "news_categories"
        ordering = ["order", "code"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name_en


class NewsArticle(BaseModel):
    class ContentType(models.TextChoices):
        NEWS = "news", "News (rewritten)"
        STORY = "story", "Story (original)"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft (pending review)"
        PUBLISHED = "published", "Published"
        REJECTED = "rejected", "Rejected"

    title_en = models.CharField(max_length=255)
    title_ar = models.CharField(max_length=255, blank=True)
    content_short = models.TextField(help_text="~50-word summary shown in lists")
    # v2: the full rewritten/generated article body (original wording only).
    body = models.TextField(blank=True)
    content_type = models.CharField(
        max_length=10, choices=ContentType.choices, default=ContentType.NEWS
    )
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PUBLISHED
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )
    source = models.CharField(max_length=100, blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    difficulty = models.CharField(max_length=10, default="B1", help_text="CEFR level")
    country = models.CharField(max_length=2, default="ma")
    is_global = models.BooleanField(
        default=True, help_text="Visible regardless of the reader's country"
    )
    published_date = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "news_articles"
        ordering = ["-published_date"]

    def save(self, *args, **kwargs):
        if self.expiry_date is None:
            self.expiry_date = self.published_date + timedelta(days=NEWS_TTL_DAYS)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title_en


class NewsExercise(BaseModel):
    """One of the 3 free exercises attached to a story. `template` is a code
    from the lesson exercise templates (multiple_choice / true_false /
    fill_blank), so the existing server-side correctors are reused as-is."""

    article = models.ForeignKey(
        NewsArticle, on_delete=models.CASCADE, related_name="exercises"
    )
    template = models.CharField(max_length=50)
    content = models.JSONField(default=dict)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "news_exercises"
        ordering = ["order"]

    def __str__(self):
        return f"{self.article_id} #{self.order} ({self.template})"


class NewsQuestionResult(BaseModel):
    """First graded result per (user, exercise) — the anti-farming record.

    Coins are only ever awarded on the first correct answer for a question
    (v2 §2.3); repeat submissions are corrected but never re-rewarded."""

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="news_results"
    )
    exercise = models.ForeignKey(
        NewsExercise, on_delete=models.CASCADE, related_name="results"
    )
    is_correct = models.BooleanField(default=False)
    coins_awarded = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "news_question_results"
        unique_together = [("user", "exercise")]

    def __str__(self):
        return f"{self.user_id} · {self.exercise_id} · {self.is_correct}"


class ArticleCompletion(BaseModel):
    """Marks an article fully answered by a user (all questions correct →
    completion bonus, once per article per user)."""

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="article_completions"
    )
    article = models.ForeignKey(
        NewsArticle, on_delete=models.CASCADE, related_name="completions"
    )
    all_correct = models.BooleanField(default=False)
    bonus_awarded = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "news_article_completions"
        unique_together = [("user", "article")]

    def __str__(self):
        return f"{self.user_id} · {self.article_id}"
