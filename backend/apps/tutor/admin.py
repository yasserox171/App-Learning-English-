from django.contrib import admin

from .models import AITutorSession, AITutorUsage


@admin.register(AITutorSession)
class AITutorSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "status", "terms_used", "terms_total",
                    "created_at")
    list_filter = ("status",)
    search_fields = ("user__email", "lesson__title")


@admin.register(AITutorUsage)
class AITutorUsageAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "session_count")
    search_fields = ("user__email",)
