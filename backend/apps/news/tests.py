"""News Learning tests (UX prompt 2.1)."""
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.users.models import User

from .management.commands.fetch_news import build_exercises
from .models import NewsArticle, NewsExercise


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(email="news@test.com", password="pass12345")
    client = APIClient()
    client.force_authenticate(user)
    return client, user


def _article(**kwargs):
    defaults = {
        "title_en": "Morocco Hosts the Tournament",
        "title_ar": "المغرب يستضيف البطولة",
        "content_short": "Fans travel to Morocco for the big tournament.",
        "source": "Test",
    }
    defaults.update(kwargs)
    return NewsArticle.objects.create(**defaults)


def test_daily_returns_latest_with_sanitized_exercises(auth_client):
    client, _ = auth_client
    old = _article(
        title_en="Old story",
        published_date=timezone.now() - timedelta(days=2),
    )
    latest = _article()
    NewsExercise.objects.create(
        article=latest,
        template="multiple_choice",
        content={"question": "Q?", "options": ["a", "b"], "correct_index": 1},
        order=0,
    )

    resp = client.get(reverse("v1:news-daily"))
    assert resp.status_code == 200
    assert resp.data["title_en"] == latest.title_en
    assert resp.data["title_ar"] == latest.title_ar
    ex = resp.data["exercises"][0]
    assert "correct_index" not in ex["content"]
    assert ex["content"]["options"] == ["a", "b"]
    assert old.title_en != resp.data["title_en"]


def test_daily_and_archive_exclude_expired(auth_client):
    client, _ = auth_client
    _article(
        title_en="Expired story",
        published_date=timezone.now() - timedelta(days=10),
        expiry_date=timezone.now() - timedelta(days=3),
    )
    resp = client.get(reverse("v1:news-daily"))
    assert resp.status_code == 404
    resp = client.get(reverse("v1:news-archive"))
    rows = resp.data["results"] if isinstance(resp.data, dict) else resp.data
    assert rows == []


def test_expiry_defaults_to_seven_days(db):
    article = _article()
    assert article.expiry_date == article.published_date + timedelta(days=7)


def test_submit_corrects_server_side(auth_client):
    client, _ = auth_client
    article = _article()
    ex = NewsExercise.objects.create(
        article=article,
        template="multiple_choice",
        content={"question": "Q?", "options": ["a", "b"], "correct_index": 1},
        order=0,
    )
    url = reverse("v1:news-exercise-submit", args=[article.id, ex.id])

    resp = client.post(url, {"selected_index": 1}, format="json")
    assert resp.status_code == 200
    assert resp.data["is_correct"] is True
    assert "correct_answer" not in resp.data

    resp = client.post(url, {"selected_index": 0}, format="json")
    assert resp.data["is_correct"] is False
    assert resp.data["correct_answer"] == "b"


def test_build_exercises_shapes(db):
    exercises = build_exercises(
        "Morocco Hosts the African Tournament",
        "Fans from many countries travel to Morocco to watch the games.",
    )
    assert 2 <= len(exercises) <= 3
    templates = [e["template"] for e in exercises]
    assert "true_false" in templates
    for ex in exercises:
        if ex["template"] == "fill_blank":
            assert ex["content"]["answer"] in ex["content"]["options"]
            assert len(ex["content"]["options"]) == 4
        if ex["template"] == "multiple_choice":
            idx = ex["content"]["correct_index"]
            assert 0 <= idx < len(ex["content"]["options"])


def test_fetch_news_demo_creates_stories_and_prunes(auth_client, db):
    client, _ = auth_client
    _article(
        title_en="Ancient story",
        published_date=timezone.now() - timedelta(days=10),
        expiry_date=timezone.now() - timedelta(days=3),
    )
    call_command("fetch_news", "--demo")
    assert not NewsArticle.objects.filter(title_en="Ancient story").exists()
    # --demo seeds 3 stories so the home news list has content on day one.
    assert NewsArticle.objects.count() == 3
    article = NewsArticle.objects.get(title_en__startswith="Morocco Prepares")
    assert article.title_ar  # demo stories ship with the Arabic headline
    assert article.exercises.count() >= 2
    # running twice must not duplicate
    call_command("fetch_news", "--demo")
    assert NewsArticle.objects.count() == 3


def test_fetch_news_demo_respects_count(db):
    call_command("fetch_news", "--demo", "--count", "1")
    assert NewsArticle.objects.count() == 1
