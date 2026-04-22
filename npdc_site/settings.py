import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-secret-key')

DEBUG = os.environ.get("DEBUG", "True") == "True"

ALLOWED_HOSTS = ['127.0.0.1', '*', '.ngrok-free.dev', '.ngrok-free.app', '.ngrok.io']

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

# Last Fallback: Ollama (local on-system AI — no API key required)
# Run: ollama serve  |  ollama pull llama3.2
OLLAMA_ENABLED = True
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2')
OLLAMA_API_ENDPOINT = os.environ.get('OLLAMA_API_ENDPOINT', 'http://localhost:11434/v1/chat/completions')

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
    'stations_weather.apps.StationsWeatherConfig',  # Live Weather Station Data
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

# Connect to the official remote NCPOR databases for live weather readings
DATABASES['data_analysis'] = {
    'ENGINE': os.environ.get('WEATHER_DB_ENGINE', 'django.db.backends.postgresql'),
    'NAME': 'data_analysis',
    'USER': os.environ.get('WEATHER_DB_USER', 'postgres'),
    'PASSWORD': os.environ.get('WEATHER_DB_PASSWORD', 'postgres'),
    'HOST': os.environ.get('WEATHER_DB_HOST', '172.27.12.28'),
    'PORT': os.environ.get('WEATHER_DB_PORT', '5432'),
}
DATABASES['polardb'] = {
    'ENGINE': os.environ.get('WEATHER_DB_ENGINE', 'django.db.backends.postgresql'),
    'NAME': 'polardb',
    'USER': os.environ.get('WEATHER_DB_USER', 'postgres'),
    'PASSWORD': os.environ.get('WEATHER_DB_PASSWORD', 'postgres'),
    'HOST': os.environ.get('WEATHER_DB_HOST', '172.27.12.28'),
    'PORT': os.environ.get('WEATHER_DB_PORT', '5432'),
}

# Assign specific weather app models to route over to data_analysis or polardb
DATABASE_ROUTERS = ['stations_weather.routers.WeatherDatabaseRouter']

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


# Secure Text Captcha Settings
CAPTCHA_CHALLENGE_FUNCT = 'npdc_site.captcha_helpers.mixed_char_challenge'
CAPTCHA_CHARS = 'ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
CAPTCHA_NOISE_FUNCTIONS = (
    'captcha.helpers.noise_arcs',
    'captcha.helpers.noise_dots',
)
CAPTCHA_LETTER_ROTATION = (-10, 10)
CAPTCHA_FONT_SIZE = 30
CAPTCHA_TIMEOUT = 5  # Minutes
CAPTCHA_LENGTH = 6


CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTHENTICATION_BACKENDS = [
    'users.backends.EmailBackend',
]

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'users.backends': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.contrib.auth': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# =============================================================================
# CACHING CONFIGURATION (Phase 12)
# =============================================================================
# Using file-based cache (best for split web/DB server architecture)
# Stores large cached datasets on the local web server disk, avoiding DB network transfer
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': BASE_DIR / 'django_cache',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 500  # Number of files to keep before deleting oldest
        }
    }
}

SEARCH_CACHE_ENABLED = os.environ.get('SEARCH_CACHE_ENABLED', 'True') == 'True'
SEARCH_RATE_LIMIT = int(os.environ.get('SEARCH_RATE_LIMIT', '60'))

# =============================================================================
# DOWNLOAD CACHING CONFIGURATION
# =============================================================================
# Cache timeout for downloaded dataset files (in seconds). Default: 1 hour.
DOWNLOAD_CACHE_TIMEOUT = int(os.environ.get('DOWNLOAD_CACHE_TIMEOUT', '43200'))  # 12 hours
# Max file size (in MB) to cache. Files larger than this are served directly
# from disk to avoid filling the cache. Default: 50 MB.
DOWNLOAD_CACHE_MAX_SIZE_MB = int(os.environ.get('DOWNLOAD_CACHE_MAX_SIZE_MB', '50'))

# =============================================================================
# SMART PRE-CACHING CONFIGURATION
# =============================================================================
# Pre-cache top N popular datasets every Nth download request
PRECACHE_TRIGGER_EVERY = int(os.environ.get('PRECACHE_TRIGGER_EVERY', '11'))
PRECACHE_TOP_N = int(os.environ.get('PRECACHE_TOP_N', '10'))
PRECACHE_LOOKBACK_DAYS = int(os.environ.get('PRECACHE_LOOKBACK_DAYS', '7'))
