"""
Django settings for ocr_project project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# -------------------------------------------------
# BASE DIRECTORY
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent


# -------------------------------------------------
# LOAD .ENV FILE (SAFE + RELIABLE)
# -------------------------------------------------
ENV_PATH = BASE_DIR / ".env"

# Load only if exists (prevents crash on startup)
if ENV_PATH.exists():
    load_dotenv(dotenv_path=str(ENV_PATH), override=True)
else:
    print(f"[WARNING] .env file not found at {ENV_PATH}")


# -------------------------------------------------
# SECURITY SETTINGS
# -------------------------------------------------
SECRET_KEY = "django-insecure-d)))i5u(^*mp3sk)6_5rzk_pn!10%2fk*ffukz!sfk2jt45r-j"

DEBUG = True
ALLOWED_HOSTS = []


# -------------------------------------------------
# INSTALLED APPS
# -------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "ocr_app",
]


# -------------------------------------------------
# MIDDLEWARE
# -------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# -------------------------------------------------
# ROOT CONFIG
# -------------------------------------------------
ROOT_URLCONF = "ocr_project.urls"
WSGI_APPLICATION = "ocr_project.wsgi.application"


# -------------------------------------------------
# TEMPLATES
# -------------------------------------------------
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


# -------------------------------------------------
# DATABASE
# -------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# -------------------------------------------------
# AUTH VALIDATION
# -------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# -------------------------------------------------
# INTERNATIONALIZATION
# -------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# -------------------------------------------------
# STATIC / MEDIA
# -------------------------------------------------
STATIC_URL = "static/"

MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"


# -------------------------------------------------
# DEFAULT AUTO FIELD
# -------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# -------------------------------------------------
# AZURE CONFIG (SAFE - NO CRASH ON STARTUP)
# -------------------------------------------------
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
AZURE_KEY = os.getenv("AZURE_KEY")


# -------------------------------------------------
# DEBUG PRINT (TEMP ONLY - REMOVE LATER)
# -------------------------------------------------
print("AZURE_ENDPOINT:", "FOUND" if AZURE_ENDPOINT else "MISSING")
print("AZURE_KEY:", "FOUND" if AZURE_KEY else "MISSING")