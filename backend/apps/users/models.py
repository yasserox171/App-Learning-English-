"""User & SocialAuth models (master prompt §8).

The custom User uses email as the login identifier and a UUID primary key.
``password`` is nullable in spirit — social-auth accounts get an unusable
password. Teachers are never self-registered (created by admin only).
"""
import uuid

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models


class UserManager(BaseUserManager):
    """Manager for the email-based custom user."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            # Social-auth accounts have no usable password.
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.STUDENT)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        TEACHER = "teacher", "Teacher"
        ADMIN = "admin", "Admin"

    class LearningGoal(models.TextChoices):
        STUDY = "study", "Study"
        WORK = "work", "Work"
        TRAVEL = "travel", "Travel"
        COMMUNICATION = "communication", "Communication"

    class AppLanguage(models.TextChoices):
        AR = "ar", "Arabic"
        EN = "en", "English"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.STUDENT
    )
    native_language = models.CharField(max_length=100, blank=True)
    learning_goal = models.CharField(
        max_length=20, choices=LearningGoal.choices, blank=True
    )
    app_language = models.CharField(
        max_length=2, choices=AppLanguage.choices, default=AppLanguage.AR
    )

    # --- v2 expansion (§2.1) --------------------------------------------- #
    # Guest accounts are real User rows created automatically on first app
    # open. Registration CONVERTS the row in place (flip is_guest, attach the
    # login method) — never a new account + data migration.
    is_guest = models.BooleanField(default=False)
    # ISO 3166-1 alpha-2, auto-detected (IP header or device locale).
    country = models.CharField(max_length=2, blank=True)
    interests = models.ManyToManyField(
        "news.Category", blank=True, related_name="interested_users"
    )

    is_active = models.BooleanField(default=True)
    # is_staff is required by Django admin; admins/teachers get access in Phase 6.
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN


class SocialAuth(models.Model):
    """Links a user to an external identity provider (Google / Apple)."""

    class Provider(models.TextChoices):
        GOOGLE = "google", "Google"
        APPLE = "apple", "Apple"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="social_accounts"
    )
    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_uid = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "social_auth"
        unique_together = [("provider", "provider_uid")]

    def __str__(self):
        return f"{self.provider}:{self.provider_uid}"
