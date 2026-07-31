"""Admin panel backend (v2 §4/§5).

AdminUser is a DEDICATED model, separate from app end-users (§4.2) — the
React panel authenticates against it, and role checks are enforced in
backend permissions, not just hidden UI.
"""
import hashlib
import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.db import models

from apps.common.models import BaseModel


class AdminUser(BaseModel):
    """Panel operator with one of three roles (v2 §4.2)."""

    class Role(models.TextChoices):
        SUPER = "super", "Super Admin"          # everything + admins + API keys
        CONTENT = "content", "Content Admin"    # lessons/articles/questions only
        SUPPORT = "support", "Support Admin"    # users + manual activation only

    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255, blank=True)
    role = models.CharField(max_length=10, choices=Role.choices)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_admins",
    )
    last_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "admin_users"
        ordering = ["email"]

    # AbstractBaseUser-free password handling (this is not AUTH_USER_MODEL).
    def set_password(self, raw: str):
        self.password_hash = make_password(raw)

    def check_password(self, raw: str) -> bool:
        return check_password(raw, self.password_hash)

    # Duck-typing for DRF's IsAuthenticated-style checks.
    @property
    def is_authenticated(self):
        return True

    def __str__(self):
        return f"{self.email} ({self.role})"


class APIKey(BaseModel):
    """Content-import API key with a trust tier (v2 §5.1).

    The raw key is shown ONCE at creation; only prefix + SHA-256 hash are
    stored. `direct` publishing requires the higher trust tier — lower-trust
    keys can only submit drafts.
    """

    class Trust(models.TextChoices):
        DRAFT_ONLY = "draft_only", "Draft submissions only"
        DIRECT_PUBLISH = "direct_publish", "May publish directly"

    name = models.CharField(max_length=100)
    prefix = models.CharField(max_length=12, db_index=True)
    key_hash = models.CharField(max_length=64)
    trust_level = models.CharField(
        max_length=20, choices=Trust.choices, default=Trust.DRAFT_ONLY
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        AdminUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="api_keys",
    )
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "api_keys"
        ordering = ["-created_at"]

    @staticmethod
    def generate() -> tuple[str, str, str]:
        """Return (raw_key, prefix, sha256_hash)."""
        raw = "flk_" + secrets.token_urlsafe(32)
        return raw, raw[:12], hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def hash_key(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()

    # Duck-typing so DRF treats an API-key principal as authenticated.
    @property
    def is_authenticated(self):
        return True

    def __str__(self):
        return f"{self.name} ({self.prefix}…, {self.trust_level})"


class ImportLog(BaseModel):
    """Traceability for every import (v2 §5.1) — especially direct publishes,
    so bad content can be found and pulled quickly."""

    api_key = models.ForeignKey(
        APIKey, on_delete=models.SET_NULL, null=True, related_name="import_logs"
    )
    publish_mode = models.CharField(max_length=10)  # draft | direct
    content_id = models.CharField(max_length=64)
    content_title = models.CharField(max_length=255, blank=True)
    success = models.BooleanField(default=True)
    detail = models.TextField(blank=True)
    # created | skipped | replaced — so idempotent retries are queryable
    # rather than buried in free-text detail. Blank for failed imports.
    action = models.CharField(max_length=12, blank=True)

    class Meta:
        db_table = "import_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.publish_mode} · {self.content_id} · {self.created_at:%Y-%m-%d %H:%M}"


class AdminActionLog(BaseModel):
    """Audit trail for sensitive panel actions (manual premium activation,
    review approvals/rejections, admin/API-key management)."""

    admin = models.ForeignKey(
        AdminUser, on_delete=models.SET_NULL, null=True, related_name="actions"
    )
    action = models.CharField(max_length=50)
    target = models.CharField(max_length=255, blank=True)
    detail = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "admin_action_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.admin_id} · {self.action} · {self.target}"
