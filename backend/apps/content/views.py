"""Content read API (master prompt §10, Phase 3).

Students read content; writes happen via Django Admin (Phase 6).
"""
from rest_framework import generics, permissions

from .models import Lesson, Level, Unit
from .serializers import (
    LessonDetailSerializer,
    LessonSerializer,
    LevelSerializer,
    UnitSerializer,
)


class LevelListView(generics.ListAPIView):
    queryset = Level.objects.all().order_by("order")
    serializer_class = LevelSerializer
    permission_classes = [permissions.IsAuthenticated]


class LevelUnitsView(generics.ListAPIView):
    serializer_class = UnitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Unit.objects.filter(level_id=self.kwargs["pk"])
            .order_by("order")
        )


class UnitLessonsView(generics.ListAPIView):
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Lesson.objects.filter(unit_id=self.kwargs["pk"])
            .order_by("order")
        )


class LessonDetailView(generics.RetrieveAPIView):
    serializer_class = LessonDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Lesson.objects.prefetch_related(
        "components__vocabulary_items",
        "components__exercises__template",
        "components__video",
        "components__text_block",
    )
