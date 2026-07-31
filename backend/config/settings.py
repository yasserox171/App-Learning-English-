"""
Django settings for the English Learning LMS.

Configuration is environment-driven (see backend/.env.example).
No secrets are committed — everything sensitive comes from .env.
"""
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------- #
# Environment
# --------------------------------------------------------------------------- #
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, []),
    JWT_ACCESS_MINUTES=(int, 60),
    JWT_REFRESH_DAYS=(int, 7),
)

# Read .env if present (not required in CI / containers that inject env vars)
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

# --------------------------------------------------------------------------- #
# Applications
# --------------------------------------------------------------------------- #
DJANGO_APPS = [
    # Custom admin site with a stats dashboard (master prompt §6).
    "apps.common.admin_config.LMSAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
]

# drf-spectacular (API docs) is optional — it pulls in rpds-py which needs
# Rust to build on some platforms (e.g. Termux). Include it only if installed.
try:
    import drf_spectacular  # noqa: F401

    HAS_SPECTACULAR = True
    THIRD_PARTY_APPS.append("drf_spectacular")
except ImportError:
    HAS_SPECTACULAR = False

LOCAL_APPS = [
    "apps.common",
    "apps.users",
    "apps.content",
    "apps.exercises",
    "apps.progress",
    "apps.news",
    "apps.billing",
    "apps.tutor",
    "apps.adminpanel",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --------------------------------------------------------------------------- #
# Database (PostgreSQL)
# --------------------------------------------------------------------------- #
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://lms:lms@localhost:5432/lms",
    )
}

# --------------------------------------------------------------------------- #
# Custom user model (master prompt §8)
# --------------------------------------------------------------------------- #
AUTH_USER_MODEL = "users.User"

# --------------------------------------------------------------------------- #
# Password validation
# --------------------------------------------------------------------------- #
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --------------------------------------------------------------------------- #
# Internationalization (ar + en, RTL handled on the client)
# --------------------------------------------------------------------------- #
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("en", "English"),
    ("ar", "Arabic"),
]

# --------------------------------------------------------------------------- #
# Static & media
# --------------------------------------------------------------------------- #
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------- #
# Django REST Framework
# --------------------------------------------------------------------------- #
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
}

if HAS_SPECTACULAR:
    REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"] = "drf_spectacular.openapi.AutoSchema"

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env("JWT_ACCESS_MINUTES")),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env("JWT_REFRESH_DAYS")),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "English Learning LMS API",
    "DESCRIPTION": "REST API for the CEFR-based English learning platform.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v1",
}

# --------------------------------------------------------------------------- #
# CORS
# --------------------------------------------------------------------------- #
_cors_origins = env("CORS_ALLOWED_ORIGINS")
if _cors_origins:
    CORS_ALLOWED_ORIGINS = _cors_origins
else:
    CORS_ALLOW_ALL_ORIGINS = DEBUG

# --------------------------------------------------------------------------- #
# Media service (hosting deferred — see master prompt §7)
# --------------------------------------------------------------------------- #
# Base for every stored asset. Storage keys are relative to MEDIA_ROOT and
# carry their own kind prefix ("videos/x.mp4", "images/y.png"), so this must
# end at /media/ — NOT /media/videos/.
VIDEO_PLAYBACK_BASE_URL = env(
    "VIDEO_PLAYBACK_BASE_URL", default="http://localhost:8000/media/"
)

# Upload ceilings per kind, in MB (content import media API).
MEDIA_MAX_VIDEO_MB = env.int("MEDIA_MAX_VIDEO_MB", default=200)
MEDIA_MAX_IMAGE_MB = env.int("MEDIA_MAX_IMAGE_MB", default=10)
MEDIA_MAX_AUDIO_MB = env.int("MEDIA_MAX_AUDIO_MB", default=25)

# --------------------------------------------------------------------------- #
# Social auth (v2 §6 — verified server-side via google-auth)
# --------------------------------------------------------------------------- #
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")          # Android OAuth client
GOOGLE_WEB_CLIENT_ID = env("GOOGLE_WEB_CLIENT_ID", default="")  # Web OAuth client
APPLE_CLIENT_ID = env("APPLE_CLIENT_ID", default="")

# --------------------------------------------------------------------------- #
# Coins & premium economy (v2 §2.3) — spec defaults, adjustable here/.env
# --------------------------------------------------------------------------- #
COINS_PER_CORRECT_ANSWER = env.int("COINS_PER_CORRECT_ANSWER", default=5)
COINS_COMPLETION_BONUS = env.int("COINS_COMPLETION_BONUS", default=10)
COINS_DAILY_CAP = env.int("COINS_DAILY_CAP", default=60)

# --------------------------------------------------------------------------- #
# AI providers (v2 §2.2 pipeline + §3 AI Tutor)
# --------------------------------------------------------------------------- #
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")
CLAUDE_MODEL = env("CLAUDE_MODEL", default="claude-opus-5")
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")        # Whisper STT
GOOGLE_TTS_API_KEY = env("GOOGLE_TTS_API_KEY", default="")
GOOGLE_TTS_VOICE = env("GOOGLE_TTS_VOICE", default="en-US-Neural2-F")

# AI Tutor shared daily caps (v2 §3.5) — tier difference is config-only.
TUTOR_FREE_DAILY_SESSIONS = env.int("TUTOR_FREE_DAILY_SESSIONS", default=2)
TUTOR_PREMIUM_DAILY_SESSIONS = env.int("TUTOR_PREMIUM_DAILY_SESSIONS", default=10)
TUTOR_MAX_EXCHANGES = env.int("TUTOR_MAX_EXCHANGES", default=6)

# --------------------------------------------------------------------------- #
# Payments (v2 §7)
# --------------------------------------------------------------------------- #
ANDROID_PACKAGE_NAME = env("ANDROID_PACKAGE_NAME", default="")
GOOGLE_PLAY_SERVICE_ACCOUNT_JSON = env(
    "GOOGLE_PLAY_SERVICE_ACCOUNT_JSON", default=""
)
PLAY_PRODUCT_MONTHLY = env("PLAY_PRODUCT_MONTHLY", default="premium_monthly")
PLAY_PRODUCT_ANNUAL = env("PLAY_PRODUCT_ANNUAL", default="premium_annual")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")
STRIPE_PRICE_MONTHLY = env("STRIPE_PRICE_MONTHLY", default="")
STRIPE_PRICE_ANNUAL = env("STRIPE_PRICE_ANNUAL", default="")
CMI_MERCHANT_ID = env("CMI_MERCHANT_ID", default="")
CMI_STORE_KEY = env("CMI_STORE_KEY", default="")
CMI_GATEWAY_URL = env(
    "CMI_GATEWAY_URL", default="https://payment.cmi.co.ma/fim/est3Dgate"
)
