import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-only-change-me",
)

DEBUG = os.environ.get(
    "DEBUG",
    "False",
).lower() == "true"


ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    ".vercel.app",
]


extra_hosts = os.environ.get(
    "ALLOWED_HOSTS",
    "",
)

if extra_hosts:
    ALLOWED_HOSTS.extend(
        [
            host.strip()
            for host in extra_hosts.split(",")
            if host.strip()
        ]
    )


INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "corsheaders",
]


MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]


ROOT_URLCONF = "vidswift_api.urls"

WSGI_APPLICATION = "vidswift_api.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------
# SaveAPI
# ---------------------------------------------------------

SAVEAPI_KEY = os.environ.get(
    "SAVEAPI_KEY",
    "",
).strip()


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

frontend_url = os.environ.get(
    "FRONTEND_URL",
    "https://vidswift-download.netlify.app",
).strip().rstrip("/")


CORS_ALLOWED_ORIGINS = [
    frontend_url,
]


CORS_URLS_REGEX = r"^/api/.*$"