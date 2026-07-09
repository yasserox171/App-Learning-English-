"""Achievement badges (UX prompt 3.2).

The catalog and unlock rules are code, not rows: `evaluate` recomputes each
rule from existing tracking data and inserts any newly satisfied badge, so
achievements stay consistent no matter where progress came from. The API
returns the full catalog with unlocked flags plus the just-unlocked batch
(the app pops a dialog for those).
"""
from django.utils import timezone

from apps.exercises.models import PronunciationAttempt

from .models import Certificate, Progress, UserAchievement, VocabularyProgress
from .services import compute_streak

# type -> (icon, title_en, title_ar, description_en, description_ar)
CATALOG = {
    "first_lesson": (
        "🏆", "First Lesson", "أول درس",
        "Complete your first lesson", "أكمل درسك الأول",
    ),
    "streak_7": (
        "🌟", "7-Day Streak", "مواظبة 7 أيام",
        "Learn 7 days in a row", "تعلّم 7 أيام متتالية",
    ),
    "vocab_100": (
        "📚", "Vocabulary Collector", "جامع المفردات",
        "Learn 100 words", "تعلّم 100 كلمة",
    ),
    "pronunciation_50": (
        "🎤", "Pronunciation Master", "سيّد النطق",
        "Practise pronunciation 50 times", "تدرّب على النطق 50 مرة",
    ),
    "level_master": (
        "👑", "Level Master", "سيّد المستوى",
        "Complete a full level", "أكمل مستوى كاملاً",
    ),
}


def _satisfied(user) -> set:
    """Achievement types the user's data currently satisfies."""
    types = set()
    if Progress.objects.filter(
        user=user, status=Progress.Status.COMPLETED
    ).exists():
        types.add("first_lesson")
    if compute_streak(user) >= 7:
        types.add("streak_7")
    learned = VocabularyProgress.objects.filter(
        user=user,
        status__in=[
            VocabularyProgress.Status.LEARNED,
            VocabularyProgress.Status.MASTERED,
        ],
    ).count()
    if learned >= 100:
        types.add("vocab_100")
    if PronunciationAttempt.objects.filter(user=user).count() >= 50:
        types.add("pronunciation_50")
    if Certificate.objects.filter(user=user).exists():
        types.add("level_master")
    return types


def evaluate(user) -> list:
    """Insert newly satisfied badges; returns the just-unlocked types."""
    have = set(
        UserAchievement.objects.filter(user=user)
        .values_list("achievement_type", flat=True)
    )
    fresh = [t for t in _satisfied(user) if t not in have and t in CATALOG]
    UserAchievement.objects.bulk_create(
        [UserAchievement(user=user, achievement_type=t) for t in fresh]
    )
    return fresh


def catalog_payload(user) -> dict:
    fresh = evaluate(user)
    unlocked_at = dict(
        UserAchievement.objects.filter(user=user)
        .values_list("achievement_type", "unlocked_at")
    )
    badges = []
    for a_type, (icon, title_en, title_ar, desc_en, desc_ar) in CATALOG.items():
        at = unlocked_at.get(a_type)
        badges.append({
            "type": a_type,
            "icon": icon,
            "title_en": title_en,
            "title_ar": title_ar,
            "description_en": desc_en,
            "description_ar": desc_ar,
            "unlocked": at is not None,
            "unlocked_at": timezone.localtime(at).isoformat() if at else None,
        })
    return {"badges": badges, "newly_unlocked": fresh}
