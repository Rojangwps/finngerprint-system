import os
from pathlib import Path
from dotenv import load_dotenv

# ------------------------------
# BASE DIRECTORY
# ------------------------------
BASE_DIR = Path(r"C:\PWD_SYS\say_thankyou_master-main")

# ------------------------------
# LOAD ENV VARIABLES
# ------------------------------
dotenv_path = BASE_DIR / ".env"
if not dotenv_path.exists():
    raise FileNotFoundError(f".env file not found at {dotenv_path}")
load_dotenv(dotenv_path=dotenv_path)

# ------------------------------
# SECURITY
# ------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key") 
DEBUG = True
ALLOWED_HOSTS = []

# ------------------------------
# APPS
# ------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "pwd",
]

# ------------------------------
# MIDDLEWARE
# ------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "pwd_sys.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.media",
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "pwd_sys.wsgi.application"

# ------------------------------
# DATABASE
# ------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

# ------------------------------
# PASSWORD VALIDATION
# ------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------
# INTERNATIONALIZATION
# ------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ------------------------------
# STATIC FILES
# ------------------------------
STATIC_URL = "/static/"
# STATICFILES_DIRS = [BASE_DIR / 'static']  # Optional

# ------------------------------
# MEDIA
# ------------------------------
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ------------------------------
# DEFAULT AUTO FIELD
# ------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------
# AUTHENTICATION
# ------------------------------
AUTHENTICATION_BACKENDS = []
SESSION_ENGINE = "django.contrib.sessions.backends.db"
# Fingerprint serial settings — set the COM port only (no commands!)
FINGERPRINT_SERIAL_PORT = "COM5"
FINGERPRINT_BAUD = 9600
# Optional timeouts
FINGERPRINT_SERIAL_TIMEOUT = 60

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]