"""News serializers — student-facing exercise content is sanitized exactly
like lesson exercises (answers never reach the client)."""
from rest_framework import serializers

from apps.exercises.serializers import ANSWER_KEYS

from .models import NewsArticle, NewsExercise


class NewsExerciseSerializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()

    class Meta:
        model = NewsExercise
        fields = ("id", "template", "content", "order")

    def get_content(self, obj):
        content = dict(obj.content or {})
        for key in ANSWER_KEYS:
            content.pop(key, None)
        return content


class NewsArticleSerializer(serializers.ModelSerializer):
    exercises = NewsExerciseSerializer(many=True, read_only=True)

    class Meta:
        model = NewsArticle
        fields = (
            "id",
            "title_en",
            "title_ar",
            "content_short",
            "source",
            "image_url",
            "difficulty",
            "country",
            "published_date",
            "exercises",
        )


class NewsArticleListSerializer(serializers.ModelSerializer):
    """Archive rows — no exercises, keeps the payload small."""

    class Meta:
        model = NewsArticle
        fields = (
            "id",
            "title_en",
            "title_ar",
            "source",
            "image_url",
            "difficulty",
            "published_date",
        )
