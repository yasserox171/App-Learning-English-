"""Auth routes (master prompt §10) — mounted under /api/v1/auth/."""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AppleLoginView,
    GoogleLoginView,
    GuestView,
    LoginView,
    MeView,
    RegisterView,
)

urlpatterns = [
    path("guest", GuestView.as_view(), name="guest"),
    path("register", RegisterView.as_view(), name="register"),
    path("login", LoginView.as_view(), name="login"),
    path("refresh", TokenRefreshView.as_view(), name="refresh"),
    path("social/google", GoogleLoginView.as_view(), name="social-google"),
    path("social/apple", AppleLoginView.as_view(), name="social-apple"),
    path("me", MeView.as_view(), name="me"),
]
