"""AI Tutor tests (v2 §3): caps, prompt, vocab diffing, turn flow (mocked)."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.content.models import (
    Lesson, LessonComponent, Level, Unit, VocabularyItem,
)
from apps.tutor import providers, services
from apps.tutor.models import AITutorSession
from apps.users.models import User


@pytest.fixture
def lesson(db):
    level = Level.objects.create(code="A1", name="Breakthrough", order=1)
    unit = Unit.objects.create(level=level, title="Food", order=1)
    lesson = Lesson.objects.create(unit=unit, title="At the restaurant", order=1)
    comp = LessonComponent.objects.create(
        lesson=lesson, type=LessonComponent.Type.VOCABULARY, order=1
    )
    for i, (word, tr) in enumerate(
        [("menu", "قائمة"), ("waiter", "نادل"), ("order", "يطلب")]
    ):
        VocabularyItem.objects.create(
            component=comp, word=word, translation=tr, order=i
        )
    return lesson


@pytest.fixture
def user(db):
    return User.objects.create_user(email="t@test.com", password="pass12345")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


def test_system_prompt_contains_topic_level_vocab(lesson, user):
    session = services.start_session(user, lesson)
    assert "At the restaurant" in session.system_prompt
    assert "A1" in session.system_prompt
    assert "menu" in session.system_prompt
    assert session.terms_total == 3


def test_daily_cap_shared_across_lessons(lesson, user):
    for _ in range(services.FREE_DAILY_SESSIONS):
        services.start_session(user, lesson)
    with pytest.raises(services.DailyCapReached):
        services.start_session(user, lesson)


def test_premium_users_get_higher_cap(lesson, user):
    from apps.billing.models import PremiumGrant
    from apps.billing.services import grant_premium

    grant_premium(user, 30, PremiumGrant.Source.SUBSCRIPTION_MONTHLY)
    assert services.daily_cap(user) == services.PREMIUM_DAILY_SESSIONS


def test_vocab_diffing_counts_target_terms(lesson, user):
    """§3.4: diff learner utterances against the target list."""
    session = services.start_session(user, lesson)
    session.turns = [
        {"role": "assistant", "text": "Welcome! What would you like?"},
        {"role": "user", "text": "I look at the menu and call the waiter."},
        {"role": "assistant", "text": "Great!"},
        {"role": "user", "text": "The menus are nice."},  # 'menus' ≠ 'menu' whole-word
    ]
    services.end_session(session)
    assert session.terms_used == 2  # menu + waiter, not order


def test_turn_flow_with_mocked_providers(client, lesson, user, monkeypatch):
    monkeypatch.setattr(
        providers.llm, "reply",
        lambda system_prompt, turns: "Nice! What food do you like?",
    )
    monkeypatch.setattr(
        providers.tts, "synthesize", lambda text: b"FAKE_MP3"
    )
    resp = client.post(reverse("v1:tutor-session-start"),
                       {"lesson_id": str(lesson.id)}, format="json")
    assert resp.status_code == 201
    session_id = resp.data["session_id"]
    assert resp.data["opening_text"]
    assert resp.data["opening_audio_b64"]  # base64 of the fake mp3

    resp = client.post(
        reverse("v1:tutor-session-turn", args=[session_id]),
        {"text": "I like couscous from the menu"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["transcript"] == "I like couscous from the menu"
    assert resp.data["reply_text"]
    assert resp.data["exchange"] == 1

    resp = client.post(reverse("v1:tutor-session-end", args=[session_id]))
    assert resp.status_code == 200
    assert resp.data["terms_used"] == 1  # "menu"


def test_turn_capped_at_max_exchanges(client, lesson, user, monkeypatch):
    monkeypatch.setattr(providers.llm, "reply", lambda s, t: "Okay!")
    monkeypatch.setattr(
        providers.tts, "synthesize",
        lambda text: (_ for _ in ()).throw(providers.ProviderError("off")),
    )
    resp = client.post(reverse("v1:tutor-session-start"),
                       {"lesson_id": str(lesson.id)}, format="json")
    session_id = resp.data["session_id"]
    for i in range(services.MAX_TURNS):
        resp = client.post(
            reverse("v1:tutor-session-turn", args=[session_id]),
            {"text": f"turn {i}"}, format="json",
        )
        assert resp.status_code == 200
    assert resp.data["ended"] is True
    session = AITutorSession.objects.get(id=session_id)
    assert session.status == AITutorSession.Status.COMPLETED
