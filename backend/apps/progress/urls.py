"""Progress / placement / certificate routes (master prompt §10)."""
from django.urls import path

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
    # Certificates
    path("certificates", CertificateListView.as_view(), name="certificate-list"),
    path("certificates/<uuid:pk>/pdf", CertificatePdfView.as_view(), name="certificate-pdf"),
]
