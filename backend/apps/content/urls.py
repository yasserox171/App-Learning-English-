"""Content routes (master prompt §10) — mounted under /api/v1/."""
from django.urls import path

from .views import (
    LessonDetailView,
    LevelListView,
    LevelUnitsView,
    UnitLessonsView,
)

urlpatterns = [
    path("levels", LevelListView.as_view(), name="level-list"),
    path("levels/<uuid:pk>/units", LevelUnitsView.as_view(), name="level-units"),
    path("units/<uuid:pk>/lessons", UnitLessonsView.as_view(), name="unit-lessons"),
    path("lessons/<uuid:pk>", LessonDetailView.as_view(), name="lesson-detail"),
]
