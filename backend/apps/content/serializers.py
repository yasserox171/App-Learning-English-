"""Content serializers (master prompt §10, Phase 3).

Read-only for students. The lesson detail returns components in order, each
with its typed payload (video / vocabulary / text / exercises).
"""
from rest_framework import serializers

from apps.common.services import video_service
from apps.exercises.serializers import ExerciseSerializer

from .models import (
    Lesson,
    LessonComponent,
    Level,
    TextBlock,
    Unit,
    Video,
    VocabularyItem,
)


class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = ("id", "code", "name", "name_fr", "order", "is_free")


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ("id", "level", "title", "order", "description")


class LessonSerializer(serializers.ModelSerializer):
    """Lightweight lesson (list view)."""

    class Meta:
        model = Lesson
        fields = ("id", "unit", "title", "order", "description")


class VideoSerializer(serializers.ModelSerializer):
    playback_url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = ("id", "title", "duration", "status", "playback_url")

    def get_playback_url(self, obj):
        # Hosting isolated behind the service layer (master prompt §7).
        return video_service.get_playback_url(obj)


class VocabularyItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = VocabularyItem
        fields = ("id", "word", "translation", "audio_url", "image_url",
                  "example_sentence", "order")


class TextBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = TextBlock
        fields = ("id", "content")


class LessonComponentSerializer(serializers.ModelSerializer):
    """A component plus its typed payload, chosen by ``type``."""

    payload = serializers.SerializerMethodField()

    class Meta:
        model = LessonComponent
        fields = ("id", "type", "order", "config", "payload")

    def get_payload(self, obj):
        if obj.type == LessonComponent.Type.VIDEO:
            video = getattr(obj, "video", None)
            return VideoSerializer(video, context=self.context).data if video else None
        if obj.type == LessonComponent.Type.VOCABULARY:
            items = obj.vocabulary_items.all()
            return VocabularyItemSerializer(items, many=True).data
        if obj.type == LessonComponent.Type.TEXT:
            block = getattr(obj, "text_block", None)
            return TextBlockSerializer(block).data if block else None
        if obj.type == LessonComponent.Type.EXERCISE:
            exercises = obj.exercises.all()
            return ExerciseSerializer(exercises, many=True).data
        return None


class LessonDetailSerializer(serializers.ModelSerializer):
    """Full lesson with ordered components (master prompt §6)."""

    components = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ("id", "unit", "title", "order", "description", "components")

    def get_components(self, obj):
        components = obj.components.all().order_by("order")
        return LessonComponentSerializer(
            components, many=True, context=self.context
        ).data
