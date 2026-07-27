"""Payment providers (v2 §7).

Four channels, all funneling into the same billing.services.grant_premium():
  - Google Play Billing (Android app — mandatory there). Server-side
    verification against the Play Developer API + RTDN webhook. A client
    "purchase successful" signal alone is NEVER trusted (§7.5).
  - Stripe (web, international cards) — Checkout Session + signed webhook.
  - CMI (web, Moroccan cards) — hosted page + hash-verified callback.
  - WhatsApp / bank transfer — manual admin activation (adminpanel app).
"""
import base64
import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request

from django.conf import settings

# --------------------------------------------------------------------------- #
# Plans (v2 §7.4). Prices are configured at the provider (Play Console /
# Stripe dashboard / CMI) which also handles local-currency display — the
# backend only maps plan codes to premium duration.
# --------------------------------------------------------------------------- #
PLANS = {
    "monthly": {
        "days": 30,
        "usd": 6,
        "source": "subscription_monthly",
        "play_product_id": getattr(
            settings, "PLAY_PRODUCT_MONTHLY", "premium_monthly"
        ),
        "stripe_price_id": getattr(settings, "STRIPE_PRICE_MONTHLY", ""),
    },
    "annual": {
        "days": 365,
        "usd": 60,
        "source": "subscription_annual",
        "play_product_id": getattr(
            settings, "PLAY_PRODUCT_ANNUAL", "premium_annual"
        ),
        "stripe_price_id": getattr(settings, "STRIPE_PRICE_ANNUAL", ""),
    },
}


def plan_for_play_product(product_id: str):
    for code, plan in PLANS.items():
        if plan["play_product_id"] == product_id:
            return code, plan
    return None, None


class PaymentError(Exception):
    pass


# --------------------------------------------------------------------------- #
# Google Play — server-side purchase verification (§7.5)
# --------------------------------------------------------------------------- #
class GooglePlayVerifier:
    """Verifies subscription purchases against the Play Developer API using a
    service-account credential (GOOGLE_PLAY_SERVICE_ACCOUNT_JSON path)."""

    SCOPE = "https://www.googleapis.com/auth/androidpublisher"

    def __init__(self):
        self.package_name = getattr(settings, "ANDROID_PACKAGE_NAME", "")
        self.credentials_path = getattr(
            settings, "GOOGLE_PLAY_SERVICE_ACCOUNT_JSON", ""
        )

    @property
    def configured(self) -> bool:
        return bool(self.package_name and self.credentials_path)

    def _access_token(self) -> str:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_file(
            self.credentials_path, scopes=[self.SCOPE]
        )
        creds.refresh(Request())
        return creds.token

    def verify_subscription(self, product_id: str, purchase_token: str) -> dict:
        """Fetch the purchase state from Google. Raises PaymentError unless
        the subscription is genuinely paid and unexpired."""
        if not self.configured:
            raise PaymentError("Google Play verification is not configured")

        url = (
            "https://androidpublisher.googleapis.com/androidpublisher/v3/"
            f"applications/{self.package_name}/purchases/subscriptions/"
            f"{urllib.parse.quote(product_id)}/tokens/"
            f"{urllib.parse.quote(purchase_token)}"
        )
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {self._access_token()}"}
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.load(resp)
        except Exception as exc:
            raise PaymentError(f"Play API verification failed: {exc}") from exc

        expiry_ms = int(data.get("expiryTimeMillis", 0))
        if expiry_ms <= time.time() * 1000:
            raise PaymentError("Subscription is expired")
        # paymentState 1 = received, 2 = free trial. 0 = pending → reject.
        if data.get("paymentState") not in (1, 2):
            raise PaymentError("Payment is not in a received state")
        return data


def decode_rtdn(body: bytes) -> dict:
    """Decode a Real-Time Developer Notification (Pub/Sub push envelope)."""
    envelope = json.loads(body.decode("utf-8"))
    data = envelope.get("message", {}).get("data", "")
    if not data:
        raise PaymentError("Empty RTDN message")
    return json.loads(base64.b64decode(data).decode("utf-8"))


# --------------------------------------------------------------------------- #
# Stripe (web) — Checkout Session + webhook signature verification
# --------------------------------------------------------------------------- #
class StripeGateway:
    API = "https://api.stripe.com/v1"

    def __init__(self):
        self.secret_key = getattr(settings, "STRIPE_SECRET_KEY", "")
        self.webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")

    @property
    def configured(self) -> bool:
        return bool(self.secret_key)

    def _post(self, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            f"{self.API}{path}",
            data=urllib.parse.urlencode(payload).encode(),
            headers={"Authorization": f"Bearer {self.secret_key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.load(resp)
        except Exception as exc:
            raise PaymentError(f"Stripe API error: {exc}") from exc

    def create_checkout_session(self, *, user, plan_code: str,
                                success_url: str, cancel_url: str) -> dict:
        plan = PLANS.get(plan_code)
        if plan is None:
            raise PaymentError(f"Unknown plan '{plan_code}'")
        if not self.configured:
            raise PaymentError("Stripe is not configured")

        payload = {
            "mode": "subscription",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "client_reference_id": str(user.id),
            "metadata[user_id]": str(user.id),
            "metadata[plan_code]": plan_code,
        }
        if plan["stripe_price_id"]:
            payload["line_items[0][price]"] = plan["stripe_price_id"]
            payload["line_items[0][quantity]"] = 1
        else:  # fallback ad-hoc price when no dashboard price is configured
            payload.update({
                "line_items[0][price_data][currency]": "usd",
                "line_items[0][price_data][unit_amount]": plan["usd"] * 100,
                "line_items[0][price_data][recurring][interval]":
                    "month" if plan_code == "monthly" else "year",
                "line_items[0][price_data][product_data][name]":
                    f"Focus Languages Premium ({plan_code})",
                "line_items[0][quantity]": 1,
            })
        session = self._post("/checkout/sessions", payload)
        return {"session_id": session["id"], "url": session.get("url", "")}

    def verify_webhook(self, payload: bytes, sig_header: str) -> dict:
        """Verify Stripe-Signature (t=..,v1=..) and return the parsed event."""
        if not self.webhook_secret:
            raise PaymentError("Stripe webhook secret is not configured")
        parts = dict(
            kv.split("=", 1) for kv in sig_header.split(",") if "=" in kv
        )
        timestamp, signature = parts.get("t", ""), parts.get("v1", "")
        signed = f"{timestamp}.".encode() + payload
        expected = hmac.new(
            self.webhook_secret.encode(), signed, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise PaymentError("Invalid Stripe webhook signature")
        return json.loads(payload.decode("utf-8"))


# --------------------------------------------------------------------------- #
# CMI (web, Morocco) — hosted payment page + hash-verified callback
# --------------------------------------------------------------------------- #
class CMIGateway:
    """CMI e-payment (hosted page, HASH ver3: SHA512 over sorted params +
    store key, base64-encoded)."""

    def __init__(self):
        self.merchant_id = getattr(settings, "CMI_MERCHANT_ID", "")
        self.store_key = getattr(settings, "CMI_STORE_KEY", "")
        self.gateway_url = getattr(
            settings, "CMI_GATEWAY_URL",
            "https://payment.cmi.co.ma/fim/est3Dgate",
        )

    @property
    def configured(self) -> bool:
        return bool(self.merchant_id and self.store_key)

    def _hash(self, params: dict) -> str:
        plain = "|".join(
            str(params[k]).replace("\\", "\\\\").replace("|", "\\|")
            for k in sorted(params, key=str.lower)
            if k.lower() not in ("hash", "encoding")
        )
        plain += f"|{self.store_key}"
        return base64.b64encode(hashlib.sha512(plain.encode()).digest()).decode()

    def build_payment_form(self, *, user, plan_code: str, order_id: str,
                           ok_url: str, fail_url: str, callback_url: str) -> dict:
        plan = PLANS.get(plan_code)
        if plan is None:
            raise PaymentError(f"Unknown plan '{plan_code}'")
        if not self.configured:
            raise PaymentError("CMI is not configured")
        params = {
            "clientid": self.merchant_id,
            "oid": order_id,
            "amount": str(plan["usd"] * 10),  # MAD approximation; configure real pricing at CMI
            "currency": "504",  # MAD
            "trantype": "PreAuth",
            "storetype": "3D_PAY_HOSTING",
            "hashAlgorithm": "ver3",
            "lang": "ar",
            "okUrl": ok_url,
            "failUrl": fail_url,
            "callbackUrl": callback_url,
            "email": user.email,
            "rnd": str(int(time.time())),
        }
        params["HASH"] = self._hash(params)
        return {"gateway_url": self.gateway_url, "fields": params}

    def verify_callback(self, post_params: dict) -> bool:
        received = post_params.get("HASH", "")
        expected = self._hash(
            {k: v for k, v in post_params.items() if k != "HASH"}
        )
        return hmac.compare_digest(received, expected)


google_play = GooglePlayVerifier()
stripe_gateway = StripeGateway()
cmi_gateway = CMIGateway()
