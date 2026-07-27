"""Coins & premium economy tests (v2 §2.3/§2.4 critical rules)."""
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.billing import services
from apps.billing.models import CoinTransaction, PremiumGrant
from apps.users.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(email="coins@test.com", password="pass12345")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


def test_award_coins_respects_daily_cap(user):
    total = 0
    for _ in range(20):  # 20 × 5 = 100 > cap of 60
        total += services.award_coins(
            user, 5, CoinTransaction.Type.EARNED_ARTICLE
        )
    assert total == services.DAILY_COIN_CAP
    assert services.balance(user) == services.DAILY_COIN_CAP
    # Once capped, further answers earn nothing (but don't error).
    assert services.award_coins(user, 5, CoinTransaction.Type.EARNED_ARTICLE) == 0


def test_award_clips_partial_amount_at_cap(user):
    services.award_coins(user, services.DAILY_COIN_CAP - 2,
                         CoinTransaction.Type.EARNED_ARTICLE)
    granted = services.award_coins(user, 5, CoinTransaction.Type.EARNED_ARTICLE)
    assert granted == 2  # clipped to remaining room


def test_redeem_requires_balance(user):
    with pytest.raises(services.CoinError):
        services.redeem_coins(user, "3_days")


def test_redeem_grants_premium_and_deducts(user):
    CoinTransaction.objects.create(
        user=user, amount=200, type=CoinTransaction.Type.EARNED_ARTICLE
    )
    grant = services.redeem_coins(user, "3_days")
    assert services.balance(user) == 0
    assert services.has_active_premium(user)
    assert (grant.end_date - grant.start_date).days == 3


def test_unknown_tier_rejected(user):
    with pytest.raises(services.CoinError):
        services.redeem_coins(user, "42_days")


def test_paid_subscription_stacks_on_coin_premium(user):
    """§2.3: paid premium bought during coin-premium EXTENDS it — never
    blocked, queued, or wasted."""
    coin_grant = services.grant_premium(user, 3, PremiumGrant.Source.COINS)
    paid_grant = services.grant_premium(
        user, 30, PremiumGrant.Source.SUBSCRIPTION_MONTHLY
    )
    # The paid period starts exactly where the coin period ends.
    assert paid_grant.start_date == coin_grant.end_date
    until = services.premium_until(user)
    expected = timezone.now() + timedelta(days=33)
    assert abs((until - expected).total_seconds()) < 120


def test_unified_premium_check_any_source(user):
    """§2.4: ONE check regardless of source."""
    assert not services.has_active_premium(user)
    services.grant_premium(user, 1, PremiumGrant.Source.MANUAL_ADMIN)
    assert services.has_active_premium(user)


def test_expired_grant_is_not_active(user):
    now = timezone.now()
    PremiumGrant.objects.create(
        user=user, start_date=now - timedelta(days=10),
        end_date=now - timedelta(days=3), source=PremiumGrant.Source.COINS,
    )
    assert not services.has_active_premium(user)


def test_wallet_endpoint(client):
    resp = client.get(reverse("v1:billing-wallet"))
    assert resp.status_code == 200
    assert resp.data["balance"] == 0
    assert resp.data["daily_cap"] == services.DAILY_COIN_CAP
    assert len(resp.data["redemption_tiers"]) == 3


def test_redeem_endpoint_manual_flow(client, user):
    CoinTransaction.objects.create(
        user=user, amount=400, type=CoinTransaction.Type.EARNED_ARTICLE
    )
    resp = client.post(reverse("v1:billing-redeem"), {"tier": "1_week"},
                       format="json")
    assert resp.status_code == 201
    assert resp.data["wallet"]["premium_active"] is True
    assert resp.data["wallet"]["balance"] == 0


def test_payment_record_replay_never_double_grants(user):
    """A replayed purchase confirmation must not extend premium twice."""
    from apps.billing.views import _record_and_grant
    from apps.billing.models import PaymentRecord

    _record_and_grant(user, provider=PaymentRecord.Provider.GOOGLE_PLAY,
                      plan_code="monthly", external_id="tok-1", raw={})
    first_until = services.premium_until(user)
    _record_and_grant(user, provider=PaymentRecord.Provider.GOOGLE_PLAY,
                      plan_code="monthly", external_id="tok-1", raw={})
    assert services.premium_until(user) == first_until
    assert PaymentRecord.objects.count() == 1
