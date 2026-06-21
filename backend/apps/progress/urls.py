"""Progress / placement / certificate routes (master prompt §10)."""
from django.urls import path

from .views import (
    CertificateListView,
    CertificatePdfView,
    LessonProgressView,
    PlacementSubmitView,
    PlacementTestView,
    ProgressOverviewView,
)

urlpatterns = [
    # Placement
    path("placement/test", PlacementTestView.as_view(), name="placement-test"),
    path("placement/submit", PlacementSubmitView.as_view(), name="placement-submit"),
    # Progress
    path("progress/overview", ProgressOverviewView.as_view(), name="progress-overview"),
    path("progress/lesson/<uuid:pk>", LessonProgressView.as_view(), name="progress-lesson"),
    # Certificates
    path("certificates", CertificateListView.as_view(), name="certificate-list"),
    path("certificates/<uuid:pk>/pdf", CertificatePdfView.as_view(), name="certificate-pdf"),
]
