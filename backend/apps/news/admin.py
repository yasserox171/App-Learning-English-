from django.contrib import admin

from .models import NewsArticle, NewsExercise


class NewsExerciseInline(admin.TabularInline):
    model = NewsExercise
    extra = 0


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = (
        "title_en",
        "source",
        "difficulty",
        "country",
        "published_date",
        "expiry_date",
    )
    search_fields = ("title_en", "title_ar")
    list_filter = ("difficulty", "country")
    inlines = [NewsExerciseInline]
