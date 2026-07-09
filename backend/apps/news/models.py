"""News Learning models (UX prompt 2.1).

A daily bite-sized news story with 3 free auto-generated exercises. Stories
expire after 7 days; the fetch_news management command both imports new
stories (NewsAPI.org) and prunes expired ones.
"""
from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel

NEWS_TTL_DAYS = 7


class NewsArticle(BaseModel):
    title_en = models.CharField(max_length=255)
    title_ar = models.CharField(max_length=255, blank=True)
    content_short = models.TextField(help_text="~50-word summary shown in-app")
    source = models.CharField(max_length=100, blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    difficulty = models.CharField(max_length=10, default="B1")
    country = models.CharField(max_length=2, default="ma")
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
