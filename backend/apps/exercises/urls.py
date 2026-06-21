"""Exercise routes (master prompt §10) — mounted under /api/v1/exercises/."""
from django.urls import path

from .views import AttemptView

urlpatterns = [
    path("<uuid:pk>/attempt", AttemptView.as_view(), name="exercise-attempt"),
]
