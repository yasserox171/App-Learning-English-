"""Root URL configuration. All API routes live under /api/v1/."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

api_v1_patterns = [
    path("auth/", include("apps.users.urls")),
    path("", include("apps.content.urls")),
    path("exercises/", include("apps.exercises.urls")),
    path("", include("apps.progress.urls")),
    path("news/", include("apps.news.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include((api_v1_patterns, "api"), namespace="v1")),
]

# API schema / docs — only when drf-spectacular is installed (see settings).
if getattr(settings, "HAS_SPECTACULAR", False):
    from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

    urlpatterns += [
        path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/v1/docs/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
