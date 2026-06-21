"""Root URL configuration. All API routes live under /api/v1/."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

api_v1_patterns = [
    # App routers are wired in as each phase lands.
    # path("auth/", include("apps.users.urls")),        # Phase 2
    # path("", include("apps.content.urls")),           # Phase 3
    # path("exercises/", include("apps.exercises.urls")),  # Phase 4
    # path("progress/", include("apps.progress.urls")),    # Phase 5
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include((api_v1_patterns, "api"), namespace="v1")),
    # API schema / docs
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
