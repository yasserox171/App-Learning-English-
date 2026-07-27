"""Admin panel routes (mounted at /api/v1/admin-api/) and the content import
endpoint (mounted at /api/v1/content/lessons/import)."""
from django.urls import path

from . import views

app_name = "adminpanel"

admin_api_patterns = [
    path("auth/login", views.LoginView.as_view(), name="admin-login"),
    path("auth/me", views.MeView.as_view(), name="admin-me"),
    path("stats", views.StatsView.as_view(), name="admin-stats"),
    # Users & subscriptions (Support/Super)
    path("users", views.UserSearchView.as_view(), name="admin-users"),
    path("users/<uuid:pk>", views.UserDetailView.as_view(), name="admin-user-detail"),
    path("premium/activate", views.ManualActivationView.as_view(),
         name="admin-premium-activate"),
    # Content tree (Content/Super)
    path("content/tree", views.ContentTreeView.as_view(), name="admin-content-tree"),
    path("lessons/<uuid:pk>", views.AdminLessonDetailView.as_view(),
         name="admin-lesson-detail"),
    # Review queues
    path("review/lessons", views.LessonReviewQueueView.as_view(),
         name="admin-review-lessons"),
    path("review/lessons/<uuid:pk>/<str:action>",
         views.LessonReviewActionView.as_view(), name="admin-review-lesson-act"),
    path("review/articles", views.ArticleReviewQueueView.as_view(),
         name="admin-review-articles"),
    path("review/articles/<uuid:pk>/<str:action>",
         views.ArticleReviewActionView.as_view(), name="admin-review-article-act"),
    path("articles/<uuid:pk>", views.ArticleEditView.as_view(),
         name="admin-article-edit"),
    # Placement question bank
    path("placement-questions", views.PlacementQuestionListView.as_view(),
         name="admin-placement-questions"),
    path("placement-questions/<uuid:pk>",
         views.PlacementQuestionDetailView.as_view(),
         name="admin-placement-question-detail"),
    # Admin accounts + API keys (Super)
    path("admins", views.AdminUserListView.as_view(), name="admin-admins"),
    path("admins/<uuid:pk>", views.AdminUserDetailView.as_view(),
         name="admin-admin-detail"),
    path("api-keys", views.APIKeyListView.as_view(), name="admin-api-keys"),
    path("api-keys/<uuid:pk>/revoke", views.APIKeyRevokeView.as_view(),
         name="admin-api-key-revoke"),
    path("import-logs", views.ImportLogListView.as_view(),
         name="admin-import-logs"),
]
