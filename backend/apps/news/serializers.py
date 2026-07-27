"""News serializers — student-facing exercise content is sanitized exactly
like lesson exercises (answers never reach the client)."""
from rest_framework import serializers

from apps.exercises.serializers import ANSWER_KEYS

from .models import Category, NewsArticle, NewsExercise


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "code", "name_en", "name_ar", "is_default")


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
    category = CategorySerializer(read_only=True)

    class Meta:
        model = NewsArticle
        fields = (
            "id",
            "title_en",
            "title_ar",
            "content_short",
            "body",
            "content_type",
            "category",
            "source",
            "image_url",
            "difficulty",
            "country",
            "is_global",
            "published_date",
            "exercises",
        )


class NewsArticleListSerializer(serializers.ModelSerializer):
    """Feed/archive rows — no exercises/body, keeps the payload small."""

    category = serializers.SlugRelatedField(slug_field="code", read_only=True)

    class Meta:
        model = NewsArticle
        fields = (
            "id",
            "title_en",
            "title_ar",
            "content_short",
            "content_type",
            "category",
            "source",
            "image_url",
            "difficulty",
            "published_date",
        )
