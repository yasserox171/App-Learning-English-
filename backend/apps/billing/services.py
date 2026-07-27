"""Coin & premium business rules (v2 §2.3).

All numbers are configurable via settings (COIN_* / PREMIUM_*); the values
here are the spec defaults.
"""
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import CoinTransaction, PremiumGrant

# --------------------------------------------------------------------------- #
# Config (overridable in settings)
# --------------------------------------------------------------------------- #
COINS_PER_CORRECT = getattr(settings, "COINS_PER_CORRECT_ANSWER", 5)
COMPLETION_BONUS = getattr(settings, "COINS_COMPLETION_BONUS", 10)
DAILY_COIN_CAP = getattr(settings, "COINS_DAILY_CAP", 60)

# tier key → (coin cost, premium days). Redemption is MANUAL (user taps).
REDEMPTION_TIERS = getattr(
    settings,
    "COIN_REDEMPTION_TIERS",
    {
        "3_days": {"coins": 200, "days": 3},
        "1_week": {"coins": 400, "days": 7},
        "1_month": {"coins": 1500, "days": 30},
    },
)


class CoinError(Exception):
    """Raised for economy violations (insufficient balance, unknown tier)."""


def balance(user) -> int:
    return (
        CoinTransaction.objects.filter(user=user).aggregate(s=Sum("amount"))["s"]
        or 0
    )


def earned_today(user) -> int:
    today = timezone.localdate()
    return (
        CoinTransaction.objects.filter(
            user=user, amount__gt=0, created_at__date=today
        ).aggregate(s=Sum("amount"))["s"]
        or 0
    )


def award_coins(user, amount: int, type: str, reference_id: str = "") -> int:
    """Award up to ``amount`` coins, clipped to the daily cap (v2 §2.3).

    Returns the amount actually awarded (0 once the cap is reached — the
    user can keep answering, they just earn nothing further today).
    """
    if amount <= 0:
        return 0
    room = DAILY_COIN_CAP - earned_today(user)
    granted = max(0, min(amount, room))
    if granted:
        CoinTransaction.objects.create(
            user=user, amount=granted, type=type, reference_id=reference_id
        )
    return granted


@transaction.atomic
def grant_premium(user, days: int, source: str) -> PremiumGrant:
    """Create a premium period that STACKS on any remaining premium time.

    A paid subscription bought while coin-premium is active starts when the
    coin period ends — nothing is blocked, queued manually, or wasted.
    """
    now = timezone.now()
    latest = (
        PremiumGrant.objects.select_for_update()
        .filter(user=user, end_date__gt=now)
        .order_by("-end_date")
        .first()
    )
    start = latest.end_date if latest else now
    return PremiumGrant.objects.create(
        user=user,
        start_date=start,
        end_date=start + timedelta(days=days),
        source=source,
    )


def has_active_premium(user) -> bool:
    """THE unified access check (v2 §2.4): any active grant, any source."""
    now = timezone.now()
    return PremiumGrant.objects.filter(
        user=user, start_date__lte=now, end_date__gt=now
    ).exists()


def premium_until(user):
    """Latest end of the user's contiguous/overlapping premium coverage."""
    now = timezone.now()
    latest = (
        PremiumGrant.objects.filter(user=user, end_date__gt=now)
        .order_by("-end_date")
        .first()
    )
    return latest.end_date if latest else None


@transaction.atomic
def redeem_coins(user, tier_key: str) -> PremiumGrant:
    """Manual redemption of a coin tier for temporary premium (v2 §2.3)."""
    tier = REDEMPTION_TIERS.get(tier_key)
    if tier is None:
        raise CoinError(f"Unknown redemption tier '{tier_key}'")
    cost, days = tier["coins"], tier["days"]
    if balance(user) < cost:
        raise CoinError("Insufficient coin balance")

    grant = grant_premium(user, days, PremiumGrant.Source.COINS)
    CoinTransaction.objects.create(
        user=user,
        amount=-cost,
        type=CoinTransaction.Type.SPENT_PREMIUM,
        reference_id=str(grant.id),
    )
    return grant


def wallet_payload(user) -> dict:
    """Everything the wallet screen needs in one call."""
    until = premium_until(user)
    return {
        "balance": balance(user),
        "earned_today": earned_today(user),
        "daily_cap": DAILY_COIN_CAP,
        "cap_reached": earned_today(user) >= DAILY_COIN_CAP,
        "coins_per_correct": COINS_PER_CORRECT,
        "completion_bonus": COMPLETION_BONUS,
        "redemption_tiers": [
            {"key": k, **v} for k, v in REDEMPTION_TIERS.items()
        ],
        "premium_active": has_active_premium(user),
        "premium_until": until.isoformat() if until else None,
    }
