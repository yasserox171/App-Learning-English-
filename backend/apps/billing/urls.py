"""Billing routes — mounted under /api/v1/billing/."""
from django.urls import path

from .views import (
    CMICallbackView,
    CMIInitiateView,
    GooglePlayRTDNView,
    GooglePlayVerifyView,
    PlansView,
    RedeemView,
    StripeCheckoutView,
    StripeWebhookView,
    WalletView,
)

urlpatterns = [
    path("wallet", WalletView.as_view(), name="billing-wallet"),
    path("redeem", RedeemView.as_view(), name="billing-redeem"),
    path("plans", PlansView.as_view(), name="billing-plans"),
    path("google/verify", GooglePlayVerifyView.as_view(), name="billing-google-verify"),
    path("google/rtdn", GooglePlayRTDNView.as_view(), name="billing-google-rtdn"),
    path("stripe/checkout", StripeCheckoutView.as_view(), name="billing-stripe-checkout"),
    path("stripe/webhook", StripeWebhookView.as_view(), name="billing-stripe-webhook"),
    path("cmi/initiate", CMIInitiateView.as_view(), name="billing-cmi-initiate"),
    path("cmi/callback", CMICallbackView.as_view(), name="billing-cmi-callback"),
]
