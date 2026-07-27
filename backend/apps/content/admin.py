from django.contrib import admin

from apps.exercises.models import Exercise

from .models import (
    Lesson,
    LessonComponent,
    Level,
    TextBlock,
    Unit,
    Video,
    VocabularyItem,
    WordAnnotation,
    WordLevel,
)


class UnitInline(admin.TabularInline):
    model = Unit
    extra = 0
    fields = ("order", "title", "description")
    ordering = ("order",)


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ("order", "title", "description")
    ordering = ("order",)


class LessonComponentInline(admin.TabularInline):
    model = LessonComponent
    extra = 0
    fields = ("order", "type", "config")
    ordering = ("order",)


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "name_fr", "order", "is_free")
    list_editable = ("order", "is_free")
    ordering = ("order",)
    inlines = [UnitInline]


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("title", "level", "order")
    list_filter = ("level",)
    search_fields = ("title",)
    ordering = ("level", "order")
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "unit", "order", "status")
    list_filter = ("unit__level", "status")
    search_fields = ("title",)
    ordering = ("unit", "order")
    inlines = [LessonComponentInline]


# --- Inlines for editing a component's typed payload (master prompt §6) ----- #
class VideoInline(admin.StackedInline):
    model = Video
    extra = 0
    max_num = 1


class TextBlockInline(admin.StackedInline):
    model = TextBlock
    extra = 0
    max_num = 1


class VocabularyItemInline(admin.TabularInline):
    model = VocabularyItem
    extra = 1
    fields = ("order", "word", "translation", "image_url", "audio_url",
              "example_sentence")
    ordering = ("order",)


class ExerciseInline(admin.TabularInline):
    model = Exercise
    extra = 1
    fields = ("order", "template", "points", "content")
    ordering = ("order",)


@admin.register(LessonComponent)
class LessonComponentAdmin(admin.ModelAdmin):
    list_display = ("lesson", "type", "order")
    list_filter = ("type",)
    ordering = ("lesson", "order")
    inlines = [VideoInline, TextBlockInline, VocabularyItemInline, ExerciseInline]


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("title", "component", "duration", "status")
    list_filter = ("status",)


@admin.register(VocabularyItem)
class VocabularyItemAdmin(admin.ModelAdmin):
    list_display = ("word", "translation", "image_url", "component", "order")
    search_fields = ("word", "translation")


@admin.register(TextBlock)
class TextBlockAdmin(admin.ModelAdmin):
    list_display = ("component",)


@admin.register(WordLevel)
class WordLevelAdmin(admin.ModelAdmin):
    list_display = ("word", "cefr_level", "translation_ar")
    list_filter = ("cefr_level",)
    search_fields = ("word",)


@admin.register(WordAnnotation)
class WordAnnotationAdmin(admin.ModelAdmin):
    list_display = ("word", "lesson", "kind", "cefr_level", "needs_review")
    list_filter = ("kind", "needs_review", "cefr_level")
    search_fields = ("word", "lesson__title")
