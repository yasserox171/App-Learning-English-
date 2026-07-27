"""News feed personalization + coin-earning rules (v2 §2.2/§2.3)."""
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.billing import services as billing
from apps.billing.models import CoinTransaction

from .models import ArticleCompletion, NewsArticle, NewsQuestionResult


def user_level_code(user) -> str:
    """The reader's CEFR level: latest placement result, else the level
    they're actively studying, else A1."""
    if not getattr(user, "is_authenticated", False):
        return "A1"
    placement = user.placement_results.select_related("assigned_level").first()
    if placement:
        return placement.assigned_level.code
    from apps.progress.services import current_level

    current = current_level(user)
    return current["code"] if current else "A1"


def personalized_feed(user):
    """v2 §2.2 filter: category IN interests AND level = user level AND
    (country = user country OR is_global). Falls back gracefully when the
    filters would produce an empty feed."""
    qs = NewsArticle.objects.filter(
        status=NewsArticle.Status.PUBLISHED, expiry_date__gt=timezone.now()
    )

    level = user_level_code(user)
    country = getattr(user, "country", "") or ""
    interests = (
        list(user.interests.values_list("id", flat=True))
        if getattr(user, "is_authenticated", False)
        else []
    )

    filtered = qs
    if interests:
        filtered = filtered.filter(
            Q(category_id__in=interests) | Q(category__isnull=True)
        )
    filtered = filtered.filter(Q(is_global=True) | Q(country=country))

    level_qs = filtered.filter(difficulty=level)
    # Don't return an empty screen just because nothing matches the exact
    # level yet — fall back to all levels, then to the whole published set.
    if level_qs.exists():
        return level_qs
    if filtered.exists():
        return filtered
    return qs


@transaction.atomic
def submit_answer(user, exercise, is_correct: bool) -> dict:
    """Record a graded answer and award coins per the v2 economy.

    - 5 coins per correct answer, first correct submission only (anti-farm).
    - Completion bonus when every question of the article is correct.
    - All of it clipped to the daily cap (award_coins handles that).
    """
    result, created = NewsQuestionResult.objects.get_or_create(
        user=user, exercise=exercise, defaults={"is_correct": is_correct}
    )

    coins_awarded = 0
    bonus_awarded = 0

    first_correct = is_correct and (created or not result.is_correct)
    if first_correct and not created:
        result.is_correct = True

    if first_correct and result.coins_awarded == 0:
        coins_awarded = billing.award_coins(
            user,
            billing.COINS_PER_CORRECT,
            CoinTransaction.Type.EARNED_ARTICLE,
            reference_id=str(exercise.article_id),
        )
        result.coins_awarded = coins_awarded
    if not created:
        result.save()

    # Completion bonus: all of the article's questions answered correctly.
    article = exercise.article
    total = article.exercises.count()
    correct = NewsQuestionResult.objects.filter(
        user=user, exercise__article=article, is_correct=True
    ).count()
    if total > 0 and correct >= total:
        completion, comp_created = ArticleCompletion.objects.get_or_create(
            user=user, article=article, defaults={"all_correct": True}
        )
        if comp_created or completion.bonus_awarded == 0:
            bonus_awarded = billing.award_coins(
                user,
                billing.COMPLETION_BONUS,
                CoinTransaction.Type.EARNED_BONUS,
                reference_id=str(article.id),
            )
            completion.all_correct = True
            completion.bonus_awarded = bonus_awarded
            completion.save()

    return {
        "coins_awarded": coins_awarded,
        "bonus_awarded": bonus_awarded,
        "cap_reached": billing.earned_today(user) >= billing.DAILY_COIN_CAP,
        "balance": billing.balance(user),
    }
