"""Coins & premium economy (v2 §2.3/§2.4) + payment records (§7).

The single access-control question everywhere is: "does this user have ANY
active PremiumGrant right now, regardless of source?" — one unified check,
never separate logic paths per source.
"""
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel


class CoinTransaction(BaseModel):
    """Append-only coin ledger. Balance = SUM(amount)."""

    class Type(models.TextChoices):
        EARNED_ARTICLE = "earned_article", "Earned (article question)"
        EARNED_BONUS = "earned_bonus", "Earned (completion bonus)"
        SPENT_PREMIUM = "spent_premium", "Spent (premium redemption)"

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="coin_transactions"
    )
    amount = models.IntegerField(help_text="positive = earned, negative = spent")
    type = models.CharField(max_length=20, choices=Type.choices)
    reference_id = models.CharField(
        max_length=64, blank=True,
        help_text="article_id / premium_grant_id the transaction refers to",
    )

    class Meta:
        db_table = "coin_transactions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id} {self.amount:+d} ({self.type})"


class PremiumGrant(BaseModel):
    """A period of premium access, from any source (coins / paid / manual).

    Stacking (v2 §2.3): a new grant starts where the latest active one ends,
    so paid time extends coin time instead of replacing or blocking it.
    """

    class Source(models.TextChoices):
        COINS = "coins", "Coins redemption"
        SUBSCRIPTION_MONTHLY = "subscription_monthly", "Monthly subscription"
        SUBSCRIPTION_ANNUAL = "subscription_annual", "Annual subscription"
        MANUAL_ADMIN = "manual_admin", "Manual (admin)"

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="premium_grants"
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    source = models.CharField(max_length=30, choices=Source.choices)

    class Meta:
        db_table = "premium_grants"
        ordering = ["-end_date"]

    @property
    def is_active(self) -> bool:
        return self.start_date <= timezone.now() < self.end_date

    def __str__(self):
        return f"{self.user_id} · {self.source} → {self.end_date:%Y-%m-%d}"


class PaymentRecord(BaseModel):
    """One verified external payment (Play / Stripe / CMI). Manual (WhatsApp)
    activations don't create a record — they're PremiumGrants with
    source='manual_admin' plus an AdminActionLog entry."""

    class Provider(models.TextChoices):
        GOOGLE_PLAY = "google_play", "Google Play Billing"
        STRIPE = "stripe", "Stripe"
        CMI = "cmi", "CMI"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="payments"
    )
    provider = models.CharField(max_length=20, choices=Provider.choices)
    plan_code = models.CharField(max_length=30)  # monthly | annual
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    # Provider-side identifier (purchase token / session id / order id) —
    # unique so a replayed confirmation can never double-grant.
    external_id = models.CharField(max_length=512, unique=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    grant = models.ForeignKey(
        PremiumGrant, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        db_table = "payment_records"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider} · {self.plan_code} · {self.status}"
