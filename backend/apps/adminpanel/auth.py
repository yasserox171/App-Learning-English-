"""Auth for the standalone admin panel + the content-import API keys.

Admin JWTs are minted with PyJWT (separate from the end-user simplejwt
tokens); role enforcement happens in backend permission classes on every
endpoint — never just hidden UI (v2 §4.2).
"""
from datetime import datetime, timedelta, timezone as dt_timezone

import jwt
from django.conf import settings
from django.utils import timezone
from rest_framework import authentication, exceptions, permissions

from .models import AdminUser, APIKey

ADMIN_TOKEN_HOURS = 12
_AUDIENCE = "focus-admin-panel"


def issue_admin_token(admin: AdminUser) -> str:
    now = datetime.now(dt_timezone.utc)
    payload = {
        "admin_id": str(admin.id),
        "role": admin.role,
        "aud": _AUDIENCE,
        "iat": now,
        "exp": now + timedelta(hours=ADMIN_TOKEN_HOURS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


class AdminJWTAuthentication(authentication.BaseAuthentication):
    """Authorization: Bearer <admin jwt> → request.user = AdminUser."""

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Bearer "):
            return None
        token = header.split(" ", 1)[1].strip()
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=["HS256"],
                audience=_AUDIENCE,
            )
        except jwt.PyJWTError:
            return None  # not an admin token — let other authenticators try
        admin = AdminUser.objects.filter(
            id=payload.get("admin_id"), is_active=True
        ).first()
        if admin is None:
            raise exceptions.AuthenticationFailed("Admin account is disabled")
        return (admin, token)


class _RolePermission(permissions.BasePermission):
    allowed_roles: tuple = ()

    def has_permission(self, request, view):
        user = request.user
        return bool(
            isinstance(user, AdminUser)
            and user.is_active
            and user.role in self.allowed_roles
        )


class IsSuperAdmin(_RolePermission):
    allowed_roles = (AdminUser.Role.SUPER,)


class IsContentAdmin(_RolePermission):
    """Content management: lessons, articles, question bank (§4.2)."""
    allowed_roles = (AdminUser.Role.SUPER, AdminUser.Role.CONTENT)


class IsSupportAdmin(_RolePermission):
    """User management + manual subscription activation (§4.2)."""
    allowed_roles = (AdminUser.Role.SUPER, AdminUser.Role.SUPPORT)


class IsAnyAdmin(_RolePermission):
    allowed_roles = (
        AdminUser.Role.SUPER, AdminUser.Role.CONTENT, AdminUser.Role.SUPPORT
    )


# --------------------------------------------------------------------------- #
# API-key auth for the content import endpoint (v2 §5.1)
# --------------------------------------------------------------------------- #
class APIKeyAuthentication(authentication.BaseAuthentication):
    """Authorization: Bearer <api_key> → request.auth = APIKey."""

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Bearer "):
            return None
        raw = header.split(" ", 1)[1].strip()
        if not raw.startswith("flk_"):
            return None
        key = APIKey.objects.filter(
            prefix=raw[:12], key_hash=APIKey.hash_key(raw), is_active=True
        ).first()
        if key is None:
            raise exceptions.AuthenticationFailed("Invalid API key")
        key.last_used_at = timezone.now()
        key.save(update_fields=["last_used_at"])
        return (key, key)  # request.user = APIKey (duck-typed below)


class HasValidAPIKey(permissions.BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.auth, APIKey)
