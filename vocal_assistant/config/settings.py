import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth",
    "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "channels", "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

ASGI_APPLICATION = "config.asgi.application"
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": BASE_DIR / "db.sqlite3",
}}

STATIC_URL = "/static/"
STATICFILES_DIRS = []
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
REST_FRAMEWORK = {"DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"]}

# ── Assistant ──────────────────────────────────────────────────────────
ASSISTANT_NAME     = os.getenv("ASSISTANT_NAME", "Aria")
ASSISTANT_WAKE_WORD = os.getenv("ASSISTANT_WAKE_WORD", "aria")

# ── Groq AI ────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "your_groq_api_key_here")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama3-8b-8192")

# ── Vosk STT ───────────────────────────────────────────────────────────
VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH", str(BASE_DIR / "model"))

# ── pyttsx3 TTS ────────────────────────────────────────────────────────
TTS_RATE   = int(os.getenv("TTS_RATE", "160"))
TTS_VOLUME = float(os.getenv("TTS_VOLUME", "1.0"))

# ── GPIO ───────────────────────────────────────────────────────────────
LED_STATUS_PIN = int(os.getenv("LED_STATUS_PIN", "17"))
LED_LISTEN_PIN = int(os.getenv("LED_LISTEN_PIN", "27"))
BUTTON_PIN     = int(os.getenv("BUTTON_PIN", "22"))

# ── Audio ──────────────────────────────────────────────────────────────
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHUNK_SIZE  = 4096

# ── Microphone ──────────────────────────────────────────────
MIC_DEVICE_INDEX = int(os.getenv("MIC_DEVICE_INDEX", "13"))
MIC_CHANNELS = int(os.getenv("MIC_CHANNELS", "2"))