from django.contrib import admin

from .models import AdminActionLog, AdminUser, APIKey, ImportLog


@admin.register(AdminUser)
class AdminUserAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "role", "is_active", "last_login")
    list_filter = ("role", "is_active")
    search_fields = ("email", "full_name")
    exclude = ("password_hash",)


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ("name", "prefix", "trust_level", "is_active", "last_used_at")
    list_filter = ("trust_level", "is_active")


@admin.register(ImportLog)
class ImportLogAdmin(admin.ModelAdmin):
    list_display = ("publish_mode", "content_title", "success", "api_key", "created_at")
    list_filter = ("publish_mode", "success")


@admin.register(AdminActionLog)
class AdminActionLogAdmin(admin.ModelAdmin):
    list_display = ("admin", "action", "target", "created_at")
    list_filter = ("action",)
