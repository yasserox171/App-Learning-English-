"""Progress / placement / certificate routes (master prompt §10)."""
from django.urls import path

from .stats import (
    GrammarSkillsView,
    StatsOverviewView,
    TimeInvestmentView,
    VocabularyHeatmapView,
    WeakAreasView,
)
from .views import (
    CertificateListView,
    CertificatePdfView,
    LessonPhaseView,
    LessonProgressView,
    PlacementSubmitView,
    PlacementTestView,
    ProgressOverviewView,
    UnitAssessmentView,
    UnitRatingView,
    VocabTrackView,
)

urlpatterns = [
    # Placement
    path("placement/test", PlacementTestView.as_view(), name="placement-test"),
    path("placement/submit", PlacementSubmitView.as_view(), name="placement-submit"),
    # Progress
    path("progress/overview", ProgressOverviewView.as_view(), name="progress-overview"),
    path("progress/lesson/<uuid:pk>", LessonProgressView.as_view(), name="progress-lesson"),
    path("progress/lesson/<uuid:pk>/phase", LessonPhaseView.as_view(), name="progress-phase"),
    # Unit mastery assessment + rating
    path("units/<uuid:pk>/assessment", UnitAssessmentView.as_view(), name="unit-assessment"),
    path("units/<uuid:pk>/rating", UnitRatingView.as_view(), name="unit-rating"),
    # Vocabulary tracking
    path("vocab/track", VocabTrackView.as_view(), name="vocab-track"),
    # Advanced stats dashboard (UX prompt 2.2)
    path("user/stats/overview", StatsOverviewView.as_view(), name="stats-overview"),
    path("user/stats/vocabulary-heatmap", VocabularyHeatmapView.as_view(), name="stats-vocab-heatmap"),
    path("user/stats/grammar-skills", GrammarSkillsView.as_view(), name="stats-grammar-skills"),
    path("user/stats/weak-areas", WeakAreasView.as_view(), name="stats-weak-areas"),
    path("user/stats/time-investment", TimeInvestmentView.as_view(), name="stats-time-investment"),
    # Certificates
    path("certificates", CertificateListView.as_view(), name="certificate-list"),
    path("certificates/<uuid:pk>/pdf", CertificatePdfView.as_view(), name="certificate-pdf"),
]
