"""Django settings for the Django page's demo: a tiny Django project wired to dpdpkit-django.

Demo only, not production settings. The database is a throwaway SQLite file, so data resets on restart.
"""

import atexit
import os
import shutil
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = "demo-only-secret-key"
DEBUG = False
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = ["dpdpkit.django"]
MIDDLEWARE = ["django.middleware.csrf.CsrfViewMiddleware"]
ROOT_URLCONF = "app.django_demo.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "app.django_demo.views.site_context",
    ]},
    }
]

# Worker threads need a file: a ":memory:" SQLite database is private to each connection.
_db_dir = tempfile.mkdtemp(prefix="dpdpkit-django-demo-")
atexit.register(shutil.rmtree, _db_dir, ignore_errors=True)
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": os.path.join(_db_dir, "demo.db")}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True

DPDPKIT = {
    "CONFIG": BASE_DIR.parent / "dpdpkit.yaml",
    "SIGNING_KEY": "demo-only-signing-key",
    "DRF": False,
    # The "login" is a stand-in: a cookie holding one of the fictional user ids in app/fastapi_demo.py.
    "PRINCIPAL_RESOLVER": "app.django_demo.views.current_user",
}
