"""v2 content pipeline (§2.2): fetch → categorize → rewrite/generate per level
→ generate questions → store as reviewable DRAFT (admins publish via the
review queue).

Usage (cron once or twice a day):
    python manage.py generate_content                     # news + stories
    python manage.py generate_content --stories-only
    python manage.py generate_content --levels A2,B1      # limit levels
    python manage.py generate_content --country ma

Requires NEWSAPI_KEY (news) and ANTHROPIC_API_KEY (rewriting/stories).
Also prunes expired articles on every run.
"""
import json
import os
import urllib.parse
import urllib.request

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.news import llm
from apps.news.models import Category, NewsArticle, NewsExercise

DEFAULT_LEVELS = ["A1", "A2", "B1", "B2"]

STORY_TOPICS = [
    "a day at the market", "an unexpected journey", "learning something new",
    "a family celebration", "helping a neighbour", "a surprise at work",
    "discovering a new city", "an old friendship",
]


class Command(BaseCommand):
    help = "Generate news rewrites and original stories as review drafts."

    def add_arguments(self, parser):
        parser.add_argument("--country", default=None)
        parser.add_argument("--levels", default=",".join(DEFAULT_LEVELS),
                            help="Comma-separated CEFR levels to generate for")
        parser.add_argument("--max-articles", type=int, default=3)
        parser.add_argument("--stories", type=int, default=1,
                            help="Original stories per level per run")
        parser.add_argument("--stories-only", action="store_true")
        parser.add_argument("--news-only", action="store_true")

    def handle(self, *args, **options):
        removed, _ = NewsArticle.objects.filter(
            expiry_date__lte=timezone.now()
        ).delete()
        if removed:
            self.stdout.write(f"Pruned {removed} expired article row(s).")

        levels = [c.strip().upper() for c in options["levels"].split(",") if c.strip()]
        country = (options["country"] or os.environ.get("NEWS_COUNTRY") or "ma").lower()
        categories = list(Category.objects.values_list("code", flat=True))

        try:
            if not options["stories_only"]:
                self._run_news(levels, country, categories, options["max_articles"])
            if not options["news_only"]:
                self._run_stories(levels, country, options["stories"])
        except llm.LLMUnavailable as exc:
            self.stderr.write(self.style.WARNING(
                f"LLM unavailable ({exc}). Nothing generated."
            ))

    # ------------------------------------------------------------------ #
    def _run_news(self, levels, country, categories, max_articles):
        api_key = os.environ.get("NEWSAPI_KEY", "")
        if not api_key:
            self.stderr.write(self.style.WARNING(
                "NEWSAPI_KEY not set — skipping news rewrites."
            ))
            return

        query = urllib.parse.urlencode(
            {"country": country, "pageSize": 15, "apiKey": api_key}
        )
        url = f"https://newsapi.org/v2/top-headlines?{query}"
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.load(resp)

        sources = [
            a for a in data.get("articles", [])
            if a.get("title") and a.get("description")
        ][:max_articles]

        for raw in sources:
            title = raw["title"].split(" - ")[0].strip()
            body = " ".join(
                filter(None, [raw.get("description"), raw.get("content")])
            )
            category_code = llm.categorize(title, body, categories)
            category = Category.objects.filter(code=category_code).first()

            for level in levels:
                if NewsArticle.objects.filter(
                    title_en__iexact=title, difficulty=level
                ).exists():
                    continue
                try:
                    result = llm.rewrite_news_article(
                        source_title=title, source_text=body, level=level
                    )
                except (llm.LLMUnavailable, ValueError, KeyError) as exc:
                    self.stderr.write(f"  rewrite failed ({title}, {level}): {exc}")
                    continue
                self._store(
                    result,
                    content_type=NewsArticle.ContentType.NEWS,
                    level=level,
                    category=category,
                    country=country,
                    source=(raw.get("source") or {}).get("name", ""),
                    image_url=raw.get("urlToImage") or "",
                )

    def _run_stories(self, levels, country, per_level):
        import random

        categories = list(Category.objects.all())
        for level in levels:
            for _ in range(per_level):
                topic = random.choice(STORY_TOPICS)
                try:
                    result = llm.generate_story(
                        topic=topic, level=level, country_hint=""
                    )
                except (llm.LLMUnavailable, ValueError, KeyError) as exc:
                    self.stderr.write(f"  story failed ({level}): {exc}")
                    continue
                self._store(
                    result,
                    content_type=NewsArticle.ContentType.STORY,
                    level=level,
                    category=random.choice(categories) if categories else None,
                    country=country,
                    source="",
                    image_url="",
                )

    @transaction.atomic
    def _store(self, result, *, content_type, level, category, country,
               source, image_url):
        article = NewsArticle.objects.create(
            title_en=result.get("title_en", "")[:255],
            title_ar=result.get("title_ar", "")[:255],
            content_short=result.get("summary", ""),
            body=result.get("body", ""),
            content_type=content_type,
            status=NewsArticle.Status.DRAFT,  # admin review before publish
            category=category,
            difficulty=level,
            country=country,
            is_global=True,
            source=source,
            image_url=image_url,
        )
        for i, q in enumerate(result.get("questions", [])[:3]):
            template = q.get("template", "")
            content = q.get("content", {})
            if template not in ("multiple_choice", "true_false", "fill_blank"):
                continue
            NewsExercise.objects.create(
                article=article, template=template, content=content, order=i
            )
        self.stdout.write(self.style.SUCCESS(
            f"  DRAFT [{content_type}/{level}] {article.title_en} "
            f"({article.exercises.count()} questions)"
        ))
