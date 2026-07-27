from django.contrib import admin

from .models import (
    Certificate,
    PlacementQuestion,
    PlacementResult,
    PlacementSession,
    Progress,
)


@admin.register(PlacementResult)
class PlacementResultAdmin(admin.ModelAdmin):
    list_display = ("user", "assigned_level", "score", "taken_at")
    list_filter = ("assigned_level",)
    search_fields = ("user__email",)
    readonly_fields = ("taken_at",)


@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "status", "score", "time_spent", "completed_at")
    list_filter = ("status",)
    search_fields = ("user__email", "lesson__title")


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("certificate_number", "user", "level", "issued_at")
    search_fields = ("certificate_number", "user__email")
    readonly_fields = ("issued_at",)


@admin.register(PlacementQuestion)
class PlacementQuestionAdmin(admin.ModelAdmin):
    list_display = ("level", "qtype", "question", "is_active")
    list_filter = ("level", "qtype", "is_active")
    search_fields = ("question",)


@admin.register(PlacementSession)
class PlacementSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "current_level", "suggested_level", "created_at")
    list_filter = ("status",)
