"""Content read API (master prompt §10, Phase 3).

Students read content; writes happen via Django Admin (Phase 6).
"""
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.progress.services import lessons_overview, units_overview

from .models import Lesson, Level
from .serializers import LessonDetailSerializer, LevelSerializer


class LevelListView(generics.ListAPIView):
    queryset = Level.objects.all().order_by("order")
    serializer_class = LevelSerializer
    permission_classes = [permissions.IsAuthenticated]


class LevelUnitsView(APIView):
    """Units of a level enriched with per-unit progress and lock state."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        return Response(units_overview(request.user, pk))


class UnitLessonsView(APIView):
    """Lessons of a unit enriched with per-lesson progress and lock state."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        return Response(lessons_overview(request.user, pk))


class LessonDetailView(generics.RetrieveAPIView):
    serializer_class = LessonDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Lesson.objects.filter(
        status=Lesson.Status.PUBLISHED
    ).prefetch_related(
        "components__vocabulary_items",
        "components__exercises__template",
        "components__video",
        "components__text_block",
    )
