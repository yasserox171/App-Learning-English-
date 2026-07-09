"""News Learning routes (UX prompt 2.1)."""
from django.urls import path

from .views import (
    DailyNewsView,
    NewsArchiveView,
    NewsArticleDetailView,
    NewsExerciseSubmitView,
)

urlpatterns = [
    path("daily", DailyNewsView.as_view(), name="news-daily"),
    path("archive", NewsArchiveView.as_view(), name="news-archive"),
    path("<uuid:pk>", NewsArticleDetailView.as_view(), name="news-detail"),
    path(
        "<uuid:article_id>/exercises/<uuid:exercise_id>/submit",
        NewsExerciseSubmitView.as_view(),
        name="news-exercise-submit",
    ),
]
