from django.contrib import admin

from .models import (
    ArticleCompletion,
    Category,
    NewsArticle,
    NewsExercise,
    NewsQuestionResult,
)


class NewsExerciseInline(admin.TabularInline):
    model = NewsExercise
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name_en", "name_ar", "is_default", "order")
    list_editable = ("is_default", "order")


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = (
        "title_en",
        "content_type",
        "status",
        "category",
        "difficulty",
        "country",
        "published_date",
    )
    search_fields = ("title_en", "title_ar")
    list_filter = ("status", "content_type", "difficulty", "country", "category")
    inlines = [NewsExerciseInline]


@admin.register(NewsQuestionResult)
class NewsQuestionResultAdmin(admin.ModelAdmin):
    list_display = ("user", "exercise", "is_correct", "coins_awarded")
    search_fields = ("user__email",)


@admin.register(ArticleCompletion)
class ArticleCompletionAdmin(admin.ModelAdmin):
    list_display = ("user", "article", "all_correct", "bonus_awarded")
    search_fields = ("user__email",)
