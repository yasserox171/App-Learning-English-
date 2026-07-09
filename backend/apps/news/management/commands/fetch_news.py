"""Import the day's news story and prune expired ones (UX prompt 2.1).

Usage:
    python manage.py fetch_news                  # NewsAPI.org (needs NEWSAPI_KEY)
    python manage.py fetch_news --country us     # override the location
    python manage.py fetch_news --demo           # offline sample story

Meant to run once a day (cron / Termux script). Every run also deletes
stories past their 7-day expiry, per the spec.
"""
import json
import random
import re
import urllib.parse
import urllib.request

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.news.models import NewsArticle, NewsExercise

# Words too common to be interesting blanks / quiz keywords.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "for", "with", "from", "into",
    "this", "that", "these", "those", "will", "would", "could", "should",
    "has", "have", "had", "was", "were", "are", "is", "be", "been", "its",
    "his", "her", "their", "our", "your", "after", "before", "over", "under",
    "about", "against", "between", "during", "says", "said", "new", "more",
}

# Plausible-but-absent options for the "which word appeared?" exercise.
_DISTRACTOR_POOL = [
    "elephant", "bicycle", "volcano", "orchestra", "sandwich", "umbrella",
    "galaxy", "waterfall", "keyboard", "lighthouse", "butterfly", "avalanche",
]


def _keywords(text: str) -> list:
    """Content words (>3 letters, not stopwords), longest first."""
    words = re.findall(r"[A-Za-z']{4,}", text)
    unique = []
    for w in words:
        lw = w.lower().strip("'")
        if lw not in _STOPWORDS and lw not in (u.lower() for u in unique):
            unique.append(w)
    return sorted(unique, key=len, reverse=True)


def build_exercises(title: str, summary: str) -> list:
    """3 free exercises derived from the story text. Formulaic on purpose —
    they are editable in the admin, and correction reuses the lesson
    correctors (multiple_choice / true_false / fill_blank)."""
    rnd = random.Random(title)  # deterministic per story
    title_kw = _keywords(title)
    body_kw = _keywords(summary)
    exercises = []

    # 1) fill_blank: complete the headline.
    if title_kw:
        blank_word = title_kw[0]
        question = re.sub(
            rf"\b{re.escape(blank_word)}\b", "_____", title, count=1
        )
        distractors = [
            w for w in title_kw[1:] + body_kw
            if w.lower() != blank_word.lower()
        ][:3]
        pool = [d for d in _DISTRACTOR_POOL if d not in distractors]
        while len(distractors) < 3:
            distractors.append(pool.pop(0))
        options = [blank_word, *distractors]
        rnd.shuffle(options)
        exercises.append({
            "template": "fill_blank",
            "content": {
                "question": f"Complete the headline: {question}",
                "answer": blank_word,
                "options": options,
            },
        })

    # 2) true_false: the headline, sometimes with one word swapped out.
    make_false = rnd.random() < 0.5 and len(title_kw) >= 2
    statement = title
    if make_false:
        statement = re.sub(
            rf"\b{re.escape(title_kw[0])}\b",
            rnd.choice(_DISTRACTOR_POOL).capitalize(),
            title,
            count=1,
        )
    exercises.append({
        "template": "true_false",
        "content": {
            "question": f'Is this what the news says? "{statement}"',
            "answer": not make_false,
        },
    })

    # 3) multiple_choice: which word appeared in the story?
    quiz_kw = body_kw[0] if body_kw else (title_kw[0] if title_kw else "")
    if quiz_kw:
        options = [quiz_kw] + rnd.sample(_DISTRACTOR_POOL, k=3)
        rnd.shuffle(options)
        exercises.append({
            "template": "multiple_choice",
            "content": {
                "question": "Which word appears in this news story?",
                "options": options,
                "correct_index": options.index(quiz_kw),
            },
        })

    return exercises


_DEMO_STORY = {
    "title": "Morocco Prepares to Host the Africa Cup of Nations",
    "title_ar": "المغرب يستعد لاستضافة كأس أمم أفريقيا",
    "description": (
        "Morocco is getting ready to welcome teams and fans from across the "
        "continent. Stadiums in six cities are being renovated, and thousands "
        "of volunteers are training to help visitors enjoy the tournament."
    ),
    "source": "Demo",
    "urlToImage": "",
}


class Command(BaseCommand):
    help = "Fetch today's news story (NewsAPI.org) and prune expired ones."

    def add_arguments(self, parser):
        parser.add_argument("--country", default=None,
                            help="2-letter country code (default: env NEWS_COUNTRY or 'ma')")
        parser.add_argument("--demo", action="store_true",
                            help="Create an offline sample story (no API key needed)")

    def handle(self, *args, **options):
        import os

        removed, _ = NewsArticle.objects.filter(
            expiry_date__lte=timezone.now()
        ).delete()
        if removed:
            self.stdout.write(f"Pruned {removed} expired news row(s).")

        country = (options["country"] or os.environ.get("NEWS_COUNTRY") or "ma").lower()

        if options["demo"]:
            raw = dict(_DEMO_STORY)
        else:
            api_key = os.environ.get("NEWSAPI_KEY", "")
            if not api_key:
                raise CommandError(
                    "NEWSAPI_KEY is not set. Get a free key at newsapi.org, "
                    "export NEWSAPI_KEY=..., or run with --demo."
                )
            raw = self._fetch_top_headline(api_key, country)
            if raw is None:
                self.stdout.write(self.style.WARNING("No usable headline today."))
                return

        title = (raw.get("title") or "").split(" - ")[0].strip()
        summary = (raw.get("description") or "").strip()

        if NewsArticle.objects.filter(title_en=title).exists():
            self.stdout.write("Today's story is already imported.")
            return

        article = NewsArticle.objects.create(
            title_en=title,
            title_ar=raw.get("title_ar", ""),
            content_short=summary,
            source=(raw.get("source") or {}).get("name", "")
            if isinstance(raw.get("source"), dict) else str(raw.get("source") or ""),
            image_url=raw.get("urlToImage") or "",
            country=country,
        )
        for i, ex in enumerate(build_exercises(title, summary)):
            NewsExercise.objects.create(
                article=article,
                template=ex["template"],
                content=ex["content"],
                order=i,
            )
        self.stdout.write(self.style.SUCCESS(
            f"Imported: {article.title_en} "
            f"({article.exercises.count()} exercises)"
        ))

    def _fetch_top_headline(self, api_key: str, country: str):
        """First top headline that has both a title and a description."""
        query = urllib.parse.urlencode({
            "country": country,
            "pageSize": 10,
            "apiKey": api_key,
        })
        url = f"https://newsapi.org/v2/top-headlines?{query}"
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.load(resp)
        for item in data.get("articles", []):
            if item.get("title") and item.get("description"):
                return item
        return None
