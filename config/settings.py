import os
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# 01 | BASE DIRECTORY AND ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env", interpolate=False)


# ============================================================
# 02 | SECURITY CONFIGURATION
# ============================================================

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

DEBUG = os.environ.get(
    "DJANGO_DEBUG", "False"
).lower() == "true"

PRODUCTION_MODE = os.environ.get(
    "DJANGO_PRODUCTION", "False"
).lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "127.0.0.1,localhost",
    ).split(",")
    if host.strip()
]

if PRODUCTION_MODE:
    DEBUG = False


# HTTPS security

SECURE_SSL_REDIRECT = PRODUCTION_MODE

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"


# Session security

SESSION_COOKIE_SECURE = PRODUCTION_MODE

SESSION_COOKIE_HTTPONLY = True

SESSION_COOKIE_SAMESITE = "Lax"


# CSRF security

CSRF_COOKIE_SECURE = PRODUCTION_MODE

CSRF_COOKIE_SAMESITE = "Lax"

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "DJANGO_CSRF_TRUSTED_ORIGINS", ""
    ).split(",")
    if origin.strip()
]


# HTTP Strict Transport Security

SECURE_HSTS_SECONDS = (
    int(os.environ.get("DJANGO_HSTS_SECONDS", "0"))
    if PRODUCTION_MODE
    else 0
)

SECURE_HSTS_INCLUDE_SUBDOMAINS = False

SECURE_HSTS_PRELOAD = False


# ============================================================
# 03 | APPLICATION CONFIGURATION
# ============================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "accounts.apps.AccountsConfig",
    "assessments",
    "opportunities.apps.OpportunitiesConfig",
]


# ============================================================
# 04 | MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# 05 | URL CONFIGURATION
# ============================================================

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"


# ============================================================
# 06 | TEMPLATE CONFIGURATION
# ============================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ============================================================
# 07 | POSTGRESQL DATABASE
# ============================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": os.environ["DB_HOST"],
        "PORT": os.environ.get("DB_PORT", "5432"),
        "OPTIONS": {
            "sslmode": os.environ.get(
                "DB_SSLMODE", "require"
            ),
            "connect_timeout": 10,
        },
    },
}


# ============================================================
# 08 | AUTHENTICATION
# ============================================================

AUTH_USER_MODEL = "accounts.CustomUser"

LOGIN_URL = "accounts:login"

LOGIN_REDIRECT_URL = "accounts:dashboard"

LOGOUT_REDIRECT_URL = "accounts:login"


# ============================================================
# 09 | PASSWORD VALIDATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ============================================================
# 10 | INTERNATIONALIZATION
# ============================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# ============================================================
# 11 | STATIC FILES
# ============================================================

STATIC_URL = "static/"


# ============================================================
# 12 | EMAIL CONFIGURATION
# ============================================================

if PRODUCTION_MODE:
    MAILERS = {
        "default": {
            "BACKEND": (
                "django.core.mail.backends.smtp.EmailBackend"
            ),
            "HOST": os.environ.get("EMAIL_HOST", ""),
            "PORT": int(
                os.environ.get("EMAIL_PORT", "587")
            ),
            "USERNAME": os.environ.get(
                "EMAIL_HOST_USER", ""
            ),
            "PASSWORD": os.environ.get(
                "EMAIL_HOST_PASSWORD", ""
            ),
            "USE_TLS": True,
        },
    }

else:
    MAILERS = {
        "default": {
            "BACKEND": (
                "django.core.mail.backends.console.EmailBackend"
            ),
        },
    }