"""Exercise serializers (master prompt §9, §10).

Student-facing content is sanitized: correct answers are never sent to the
client. Correction happens server-side via the attempt endpoint (Phase 4).
"""
from rest_framework import serializers

from .models import Exercise, ExerciseAttempt, ExerciseTemplate

# Keys that reveal the answer and must be stripped from student-facing content.
ANSWER_KEYS = ("correct_index", "answer", "correct_order")


class ExerciseTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExerciseTemplate
        fields = ("id", "code", "name", "content_schema", "is_active")


class ExerciseSerializer(serializers.ModelSerializer):
    """Sanitized exercise for students (no answer fields)."""

    template_code = serializers.CharField(source="template.code", read_only=True)
    content = serializers.SerializerMethodField()

    class Meta:
        model = Exercise
        fields = ("id", "template_code", "content", "points", "order")

    def get_content(self, obj):
        content = dict(obj.content or {})
        for key in ANSWER_KEYS:
            content.pop(key, None)
        return content


class ExerciseAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExerciseAttempt
        fields = ("id", "exercise", "answer", "is_correct", "score", "attempted_at")
        read_only_fields = ("is_correct", "score", "attempted_at")
