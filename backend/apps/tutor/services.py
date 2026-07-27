"""AI Tutor business logic (v2 §3): prompt building, caps, vocab diffing."""
import re

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.billing.services import has_active_premium
from apps.content.models import LessonComponent
from apps.news.services import user_level_code

from .models import AITutorSession, AITutorUsage

# Shared daily caps across the whole app (§3.5) — config-only tier difference.
FREE_DAILY_SESSIONS = getattr(settings, "TUTOR_FREE_DAILY_SESSIONS", 2)
PREMIUM_DAILY_SESSIONS = getattr(settings, "TUTOR_PREMIUM_DAILY_SESSIONS", 10)
MAX_TURNS = getattr(settings, "TUTOR_MAX_EXCHANGES", 6)


class TutorError(Exception):
    pass


class DailyCapReached(TutorError):
    pass


def daily_cap(user) -> int:
    return PREMIUM_DAILY_SESSIONS if has_active_premium(user) else FREE_DAILY_SESSIONS


def sessions_today(user) -> int:
    usage = AITutorUsage.objects.filter(
        user=user, date=timezone.localdate()
    ).first()
    return usage.session_count if usage else 0


def lesson_vocabulary(lesson) -> list[str]:
    words = []
    for component in lesson.components.filter(
        type=LessonComponent.Type.VOCABULARY
    ):
        words += list(
            component.vocabulary_items.values_list("word", flat=True)
        )
    return words[:10]  # 5-10 target terms (§3.1)


def build_system_prompt(lesson, level: str, vocabulary: list[str]) -> str:
    """Dynamic system prompt per §3.2."""
    vocab_line = ", ".join(vocabulary) if vocabulary else "everyday words"
    return f"""You are a friendly English tutor having a SPOKEN conversation with an
Arabic-speaking learner at CEFR level {level}. The conversation topic is the
lesson "{lesson.title}" ({lesson.unit.title}).

Rules for every reply:
- Use simple language matching CEFR {level}.
- Maximum 1-2 short sentences. This is a voice conversation, not an essay.
- Encourage the learner to naturally use these target words: {vocab_line}.
  When they use one, acknowledge it naturally ("Nice — 'boarding pass' is
  exactly the right word!").
- If they make a clear grammar mistake, gently model the correct form inside
  your reply — never a separate grammar lecture.
- Stay on the lesson's topic throughout. Warm, patient, encouraging tone.
- Usually end with a short question to keep the conversation going."""


@transaction.atomic
def start_session(user, lesson) -> AITutorSession:
    """Check the shared daily cap, then open a session (§3.5)."""
    today = timezone.localdate()
    usage, _ = AITutorUsage.objects.select_for_update().get_or_create(
        user=user, date=today
    )
    if usage.session_count >= daily_cap(user):
        raise DailyCapReached(
            f"Daily AI Tutor limit reached ({daily_cap(user)} sessions). "
            "Come back tomorrow!"
        )
    usage.session_count = F("session_count") + 1
    usage.save()

    # Close any dangling active session.
    AITutorSession.objects.filter(
        user=user, status=AITutorSession.Status.ACTIVE
    ).update(status=AITutorSession.Status.COMPLETED, ended_at=timezone.now())

    vocabulary = lesson_vocabulary(lesson)
    level = user_level_code(user)
    return AITutorSession.objects.create(
        user=user,
        lesson=lesson,
        system_prompt=build_system_prompt(lesson, level, vocabulary),
        target_vocabulary=vocabulary,
        terms_total=len(vocabulary),
    )


def count_terms_used(session: AITutorSession) -> int:
    """Diff the learner's utterances against the target list (§3.4)."""
    spoken = " ".join(
        t["text"].lower() for t in session.turns if t.get("role") == "user"
    )
    used = 0
    for term in session.target_vocabulary:
        pattern = r"\b" + re.escape(term.lower()) + r"\b"
        if re.search(pattern, spoken):
            used += 1
    return used


def end_session(session: AITutorSession) -> AITutorSession:
    session.terms_used = count_terms_used(session)
    session.status = AITutorSession.Status.COMPLETED
    session.ended_at = timezone.now()
    session.save()
    return session


def exchanges_done(session: AITutorSession) -> int:
    return sum(1 for t in session.turns if t.get("role") == "user")
