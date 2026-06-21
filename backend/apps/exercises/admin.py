from django.contrib import admin

from .models import Exercise, ExerciseAttempt, ExerciseTemplate


@admin.register(ExerciseTemplate)
class ExerciseTemplateAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    list_filter = ("is_active",)
    list_editable = ("is_active",)


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ("template", "component", "points", "order")
    list_filter = ("template__code",)
    ordering = ("component", "order")


@admin.register(ExerciseAttempt)
class ExerciseAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "exercise", "is_correct", "score", "attempted_at")
    list_filter = ("is_correct",)
    search_fields = ("user__email",)
    readonly_fields = ("attempted_at",)
