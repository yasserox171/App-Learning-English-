"""Billing endpoints: wallet/redeem (§2.3) + payment channels (§7)."""
import uuid

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import payments, services
from .models import PaymentRecord, PremiumGrant


class WalletView(APIView):
    """GET /billing/wallet — balance, caps, tiers, premium status."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(services.wallet_payload(request.user))


class RedeemView(APIView):
    """POST /billing/redeem {"tier": "3_days"} — manual coin redemption."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        tier = str(request.data.get("tier", ""))
        try:
            grant = services.redeem_coins(request.user, tier)
        except services.CoinError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            {
                "granted_until": grant.end_date.isoformat(),
                "wallet": services.wallet_payload(request.user),
            },
            status=status.HTTP_201_CREATED,
        )


class PlansView(APIView):
    """GET /billing/plans — subscription plans for the payment page."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "plans": [
                    {
                        "code": code,
                        "usd": plan["usd"],
                        "days": plan["days"],
                        "play_product_id": plan["play_product_id"],
                    }
                    for code, plan in payments.PLANS.items()
                ],
                "premium_active": services.has_active_premium(request.user),
            }
        )


def _record_and_grant(user, *, provider, plan_code, external_id, raw):
    """Idempotently record a verified payment and grant premium (stacking)."""
    plan = payments.PLANS[plan_code]
    record, created = PaymentRecord.objects.get_or_create(
        external_id=external_id,
        defaults={
            "user": user,
            "provider": provider,
            "plan_code": plan_code,
            "status": PaymentRecord.Status.VERIFIED,
            "raw_payload": raw,
        },
    )
    if not created:  # replayed confirmation — never double-grant
        return record
    record.grant = services.grant_premium(user, plan["days"], plan["source"])
    record.save(update_fields=["grant"])
    return record


class GooglePlayVerifyView(APIView):
    """POST /billing/google/verify {product_id, purchase_token}.

    Verifies against the Play Developer API before activating anything —
    a client-side "purchase successful" flag alone is never trusted (§7.5).
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        product_id = str(request.data.get("product_id", ""))
        token = str(request.data.get("purchase_token", ""))
        plan_code, plan = payments.plan_for_play_product(product_id)
        if plan is None or not token:
            return Response(
                {"detail": "Unknown product or missing purchase_token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            data = payments.google_play.verify_subscription(product_id, token)
        except payments.PaymentError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_402_PAYMENT_REQUIRED
            )
        record = _record_and_grant(
            request.user,
            provider=PaymentRecord.Provider.GOOGLE_PLAY,
            plan_code=plan_code,
            external_id=token,
            raw=data,
        )
        return Response(
            {
                "status": record.status,
                "premium_until": services.premium_until(request.user),
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class GooglePlayRTDNView(APIView):
    """POST /billing/google/rtdn — Real-Time Developer Notifications
    (Pub/Sub push). Keeps renewals/cancellations in sync without polling."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        try:
            notification = payments.decode_rtdn(request.body)
        except (payments.PaymentError, ValueError):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        sub = notification.get("subscriptionNotification") or {}
        token = sub.get("purchaseToken", "")
        product_id = sub.get("subscriptionId", "")
        notif_type = sub.get("notificationType")

        record = PaymentRecord.objects.filter(external_id=token).first()

        # 2 = RENEWED, 1 = RECOVERED, 7 = RESTARTED → extend premium.
        if notif_type in (1, 2, 7) and record is not None:
            plan_code, plan = payments.plan_for_play_product(product_id)
            if plan is not None:
                renewal_id = f"{token}:{notification.get('eventTimeMillis', '')}"
                _record_and_grant(
                    record.user,
                    provider=PaymentRecord.Provider.GOOGLE_PLAY,
                    plan_code=plan_code,
                    external_id=renewal_id,
                    raw=notification,
                )
        # 3 = CANCELED, 12 = REVOKED, 13 = EXPIRED → mark; access simply
        # lapses when the last grant's end_date passes (no early revoke on
        # voluntary cancel — the paid period runs out naturally).
        elif notif_type in (12,) and record is not None:
            record.status = PaymentRecord.Status.REFUNDED
            record.save(update_fields=["status"])
            PremiumGrant.objects.filter(
                id=record.grant_id
            ).update(end_date=record.created_at)

        # Always ACK so Pub/Sub stops retrying.
        return Response({"ok": True})


class StripeCheckoutView(APIView):
    """POST /billing/stripe/checkout {"plan": "monthly", success_url, cancel_url}."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        plan_code = str(request.data.get("plan", "monthly"))
        try:
            session = payments.stripe_gateway.create_checkout_session(
                user=request.user,
                plan_code=plan_code,
                success_url=str(
                    request.data.get("success_url", "https://lms.centrefocus.ma/pay/success")
                ),
                cancel_url=str(
                    request.data.get("cancel_url", "https://lms.centrefocus.ma/pay/cancel")
                ),
            )
        except payments.PaymentError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(session)


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    """POST /billing/stripe/webhook — signature-verified events."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        from django.contrib.auth import get_user_model

        sig = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        try:
            event = payments.stripe_gateway.verify_webhook(request.body, sig)
        except payments.PaymentError:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if event.get("type") == "checkout.session.completed":
            session = event["data"]["object"]
            user_id = (session.get("metadata") or {}).get("user_id")
            plan_code = (session.get("metadata") or {}).get("plan_code", "monthly")
            user = get_user_model().objects.filter(id=user_id).first()
            if user and plan_code in payments.PLANS:
                _record_and_grant(
                    user,
                    provider=PaymentRecord.Provider.STRIPE,
                    plan_code=plan_code,
                    external_id=session["id"],
                    raw={"event_id": event.get("id", "")},
                )
        return Response({"ok": True})


class CMIInitiateView(APIView):
    """POST /billing/cmi/initiate {"plan": "monthly"} → hosted-page form."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        plan_code = str(request.data.get("plan", "monthly"))
        order_id = f"FL-{uuid.uuid4().hex[:16]}"
        try:
            form = payments.cmi_gateway.build_payment_form(
                user=request.user,
                plan_code=plan_code,
                order_id=order_id,
                ok_url=str(request.data.get("ok_url", "https://lms.centrefocus.ma/pay/success")),
                fail_url=str(request.data.get("fail_url", "https://lms.centrefocus.ma/pay/fail")),
                callback_url="https://lms.centrefocus.ma/api/v1/billing/cmi/callback",
            )
        except payments.PaymentError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        # Pre-create the pending record so the callback can find the user/plan.
        PaymentRecord.objects.create(
            user=request.user,
            provider=PaymentRecord.Provider.CMI,
            plan_code=plan_code,
            status=PaymentRecord.Status.PENDING,
            external_id=order_id,
        )
        return Response(form)


@method_decorator(csrf_exempt, name="dispatch")
class CMICallbackView(APIView):
    """POST /billing/cmi/callback — CMI server-to-server confirmation."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        params = {k: v for k, v in request.POST.items()}
        if not payments.cmi_gateway.verify_callback(params):
            return Response("FAILURE", status=status.HTTP_400_BAD_REQUEST)

        order_id = params.get("oid", "")
        approved = params.get("ProcReturnCode") == "00"
        record = PaymentRecord.objects.filter(
            external_id=order_id, provider=PaymentRecord.Provider.CMI
        ).first()
        if record is None:
            return Response("FAILURE", status=status.HTTP_404_NOT_FOUND)

        if approved and record.status == PaymentRecord.Status.PENDING:
            plan = payments.PLANS[record.plan_code]
            record.status = PaymentRecord.Status.VERIFIED
            record.grant = services.grant_premium(
                record.user, plan["days"], plan["source"]
            )
            record.raw_payload = params
            record.save()
            return Response("ACTION=POSTAUTH")
        if not approved:
            record.status = PaymentRecord.Status.FAILED
            record.save(update_fields=["status"])
        return Response("APPROVED" if approved else "FAILURE")
