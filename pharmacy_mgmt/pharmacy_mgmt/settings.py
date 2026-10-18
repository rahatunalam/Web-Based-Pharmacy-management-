from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ──────────────────────────────────────────────
# Reads from Railway environment variable in production
# Falls back to your local key during development
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-6em7nf&=#o5@x%%9cpnh9llj=^wbwun1&d#u@$94v-(x4xh5ni'
)

# False in production, True locally
# Railway will set DEBUG=False via environment variable
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# Railway will set this to your app's domain
ALLOWED_HOSTS = os.environ.get(
    'ALLOWED_HOSTS',
    'localhost,127.0.0.1'
).split(',')

CSRF_TRUSTED_ORIGINS = [
    'https://*.up.railway.app',    # ← add this
]

# ── Apps ──────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'pharmacy',
]

# ── Middleware ────────────────────────────────────────────
# whitenoise must be SECOND — right after SecurityMiddleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',          # ← add this
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'pharmacy_mgmt.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'pharmacy_mgmt.wsgi.application'

# ── Database ──────────────────────────────────────────────
# dj_database_url reads DATABASE_URL from Railway automatically
# When running locally, falls back to your PostgreSQL
DATABASES = {
    'default': dj_database_url.config(
        default='postgresql://postgres:Rahat%401520@localhost:5432/peoples_pharma',
        conn_max_age=600,
    )
}

# ── Password validation ───────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalisation ──────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Dhaka'    # ← changed from UTC to your timezone
USE_I18N = True
USE_TZ = True

# ── Static files ──────────────────────────────────────────
STATIC_URL = '/static/'

# Where your app's static files live during development
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Where collectstatic gathers everything for production
STATIC_ROOT = BASE_DIR / 'staticfiles'             # ← add this

# Whitenoise serves static files efficiently in production
STATICFILES_STORAGE = (
    'whitenoise.storage.CompressedManifestStaticFilesStorage'
)                                                   # ← add this

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Login redirect ────────────────────────────────────────
LOGIN_URL = 'pharmacy:login'
LOGIN_REDIRECT_URL = 'pharmacy:dashboard'
LOGOUT_REDIRECT_URL = 'pharmacy:login'