import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-secret-key')

DEBUG = os.environ.get("DEBUG", "True") == "True"

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '.ngrok-free.dev', '.ngrok-free.app', '.ngrok.io']

CSRF_TRUSTED_ORIGINS = ['https://*.ngrok-free.dev', 'https://*.ngrok-free.app']

# =====================================================
# AI CHATBOT CONFIGURATION (Dual Provider: Groq + OpenRouter)
# =====================================================
CHATBOT_AI_ENABLED = True

# Primary: Groq (14,400 req/day free)
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_MODEL = os.environ.get('GROQ_MODEL', 'llama-3.1-8b-instant')
GROQ_API_ENDPOINT = 'https://api.groq.com/openai/v1/chat/completions'

# Fallback: OpenRouter
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
OPENROUTER_MODEL = os.environ.get('OPENROUTER_MODEL', 'google/gemma-3-4b-it:free')
OPENROUTER_API_ENDPOINT = 'https://openrouter.ai/api/v1/chat/completions'

# Shared settings
OPENROUTER_TEMPERATURE = 0.7
OPENROUTER_MAX_TOKENS = 800
OPENROUTER_TIMEOUT = 60

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'crispy_forms',
    'crispy_bootstrap5',
    'users.apps.UsersConfig',
    'data_submission.apps.DataSubmissionConfig',
    'activity_logs.apps.ActivityLogsConfig',
    'chatbot.apps.ChatbotConfig',  # AI Chatbot Assistant
    'npdc_search.apps.DatasetSearchConfig',
    'captcha',
    'django_countries',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'activity_logs.middleware.ActivityLogMiddleware',
]

ROOT_URLCONF = 'npdc_site.urls'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_FILE_PATH = BASE_DIR / "sent_emails"


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'npdc_site.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.environ.get('DB_NAME', BASE_DIR / 'db.sqlite3'),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = 'users:login_redirect'
LOGOUT_REDIRECT_URL = 'users:login'

if DEBUG:
    # Development settings
    pass
else:
    # Production settings
    pass


# Secure Mathematical Captcha Settings
CAPTCHA_CHALLENGE_FUNCT = 'captcha.helpers.math_challenge'
CAPTCHA_NOISE_FUNCTIONS = (
    'captcha.helpers.noise_arcs',
    'captcha.helpers.noise_dots',
)
CAPTCHA_LETTER_ROTATION = (-10, 10)
CAPTCHA_FONT_SIZE = 30
CAPTCHA_TIMEOUT = 5  # Minutes


CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTHENTICATION_BACKENDS = [
    'users.backends.EmailBackend',
]

# =============================================================================
# CACHING CONFIGURATION (Phase 12)
# =============================================================================
# Using database cache (works without Redis, production-ready)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache_table',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000
        }
    }
}

SEARCH_CACHE_ENABLED = os.environ.get('SEARCH_CACHE_ENABLED', 'True') == 'True'
SEARCH_RATE_LIMIT = int(os.environ.get('SEARCH_RATE_LIMIT', '60'))
