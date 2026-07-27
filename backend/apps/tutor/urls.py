"""AI Tutor routes — mounted under /api/v1/tutor/."""
from django.urls import path

from .views import SessionEndView, SessionStartView, SessionTurnView, UsageView

urlpatterns = [
    path("usage", UsageView.as_view(), name="tutor-usage"),
    path("sessions", SessionStartView.as_view(), name="tutor-session-start"),
    path("sessions/<uuid:pk>/turn", SessionTurnView.as_view(), name="tutor-session-turn"),
    path("sessions/<uuid:pk>/end", SessionEndView.as_view(), name="tutor-session-end"),
]
