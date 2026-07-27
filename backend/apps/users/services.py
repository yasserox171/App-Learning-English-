"""Guest-account + account-conversion services (v2 §2.1, §6).

Key rule: a guest is a REAL User row. Registering (email/password or Google)
converts that same row in place — coins, interests and progress survive
automatically because the primary key never changes.
"""
import secrets
import string

from django.conf import settings
from django.db import IntegrityError

from .models import SocialAuth, User

GUEST_EMAIL_DOMAIN = "guest.local"
_GUEST_ALPHABET = string.ascii_lowercase + string.digits

# Request headers that may carry an IP-derived country code (set by a CDN /
# reverse proxy, e.g. Cloudflare's CF-IPCountry).
_COUNTRY_HEADERS = ("HTTP_CF_IPCOUNTRY", "HTTP_X_COUNTRY_CODE")


def detect_country(request, explicit: str = "") -> str:
    """Best-effort 2-letter country: client-sent device locale first,
    then proxy/CDN geo headers. Never asked directly (v2 §2.2)."""
    value = (explicit or "").strip()
    if not value:
        for header in _COUNTRY_HEADERS:
            value = (request.META.get(header) or "").strip()
            if value:
                break
    value = value.lower()
    return value if len(value) == 2 and value.isalpha() else ""


def generate_guest_code() -> str:
    return "guest_" + "".join(secrets.choice(_GUEST_ALPHABET) for _ in range(6))


def create_guest(country: str = "") -> User:
    """Create a guest User with a random code and the default interest set."""
    from apps.news.models import Category

    for _ in range(5):  # retry on the (unlikely) code collision
        code = generate_guest_code()
        try:
            user = User.objects.create_user(
                email=f"{code}@{GUEST_EMAIL_DOMAIN}",
                password=None,
                full_name=code,
                is_guest=True,
                country=country,
            )
            break
        except IntegrityError:
            continue
    else:
        raise RuntimeError("Could not allocate a unique guest code")

    user.interests.set(Category.objects.filter(is_default=True))
    return user


def convert_guest(user: User, *, email: str, password: str | None = None,
                  full_name: str = "") -> User:
    """Flip a guest row into a registered account IN PLACE (v2 §2.1)."""
    user.email = User.objects.normalize_email(email)
    if password:
        user.set_password(password)
    if full_name:
        user.full_name = full_name
    user.is_guest = False
    user.save()
    return user


# --------------------------------------------------------------------------- #
# Google Sign-In (v2 §6.1) — server-side ID-token verification.
# --------------------------------------------------------------------------- #
class GoogleVerificationError(Exception):
    pass


def verify_google_id_token(token: str) -> dict:
    """Validate signature/expiry/audience against Google (official library).

    Returns {sub, email, email_verified, name}. Never trust a client-asserted
    identity — this is the only entry point for Google login data.
    """
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise GoogleVerificationError(
            "google-auth is not installed on the server"
        ) from exc

    audiences = [
        aud
        for aud in (settings.GOOGLE_CLIENT_ID, settings.GOOGLE_WEB_CLIENT_ID)
        if aud
    ]
    if not audiences:
        raise GoogleVerificationError("Google Sign-In is not configured")

    try:
        info = google_id_token.verify_oauth2_token(
            token, google_requests.Request()
        )
    except ValueError as exc:
        raise GoogleVerificationError(str(exc)) from exc

    if info.get("aud") not in audiences:
        raise GoogleVerificationError("Token has an unexpected audience")

    return {
        "sub": info["sub"],
        "email": info.get("email", ""),
        "email_verified": bool(info.get("email_verified")),
        "name": info.get("name", ""),
    }


def google_sign_in(*, token_info: dict, requester=None) -> User:
    """Account-linking logic (v2 §6.1).

    - Existing SocialAuth for this Google sub → that user.
    - Existing user with the same (verified) email → link Google to it.
    - Authenticated guest requester → convert their row in place.
    - Otherwise → create a new user.
    """
    sub = token_info["sub"]
    email = token_info["email"]
    verified = token_info["email_verified"]
    name = token_info.get("name", "")

    social = (
        SocialAuth.objects.filter(
            provider=SocialAuth.Provider.GOOGLE, provider_uid=sub
        )
        .select_related("user")
        .first()
    )
    if social:
        user = social.user
        if user.is_guest:  # linked while still guest — finish the conversion
            convert_guest(user, email=email, full_name=name)
        return user

    if not email:
        raise GoogleVerificationError("Google token carries no email")

    existing = User.objects.filter(email__iexact=email).first()
    if existing is not None:
        # Auto-linking to an existing account requires a verified email (§6.1).
        if not verified:
            raise GoogleVerificationError(
                "Google email is not verified; cannot link to an existing account"
            )
        user = existing
        if user.is_guest:
            convert_guest(user, email=email, full_name=name)
    elif requester is not None and getattr(requester, "is_guest", False):
        user = convert_guest(requester, email=email, full_name=name)
    else:
        user = User.objects.create_user(
            email=email, password=None, full_name=name
        )

    SocialAuth.objects.create(
        user=user, provider=SocialAuth.Provider.GOOGLE, provider_uid=sub
    )
    return user
