# core/settings_prod.py
"""Configuración de producción — Render.com.

Hereda settings.py. TODO lo sensible sale de variables de entorno:

    DJANGO_SETTINGS_MODULE  → core.settings_prod
    SECRET_KEY              → obligatoria (Render: generateValue)
    DATABASE_URL            → obligatoria (Render: fromDatabase)
    ALLOWED_HOSTS           → opcional, separados por coma
    CSRF_TRUSTED_ORIGINS    → opcional, separados por coma (con https://)
    DB_SSL_REQUIRE          → "True" (default) en Render; "False" en Docker local
    FORCE_HTTPS             → "True" (default) en Render; "False" en Docker local
    EMAIL_BACKEND           → opcional; por defecto imprime los correos en el log
    RENDER_EXTERNAL_HOSTNAME→ la inyecta Render automáticamente
"""
import os

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .settings import *   # noqa: F401,F403  hereda la configuración base

# ── SEGURIDAD BÁSICA ───────────────────────────────────────────────────────
DEBUG = False
SECRET_KEY = os.environ['SECRET_KEY']   # falla a propósito si no existe


def _lista_env(nombre):
    """Lee una variable de entorno 'a,b,c' y devuelve ['a','b','c']."""
    return [x.strip() for x in os.environ.get(nombre, '').split(',') if x.strip()]


def _bool_env(nombre, defecto=True):
    """Lee una variable de entorno booleana ('True'/'False')."""
    return os.environ.get(nombre, str(defecto)).strip().lower() in ('1', 'true', 'yes')


# ── HOSTS Y CSRF ───────────────────────────────────────────────────────────
_render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '')

ALLOWED_HOSTS = ['localhost', '127.0.0.1']
if _render_host:
    ALLOWED_HOSTS.append(_render_host)
ALLOWED_HOSTS += _lista_env('ALLOWED_HOSTS')

CSRF_TRUSTED_ORIGINS = _lista_env('CSRF_TRUSTED_ORIGINS')
if _render_host:
    CSRF_TRUSTED_ORIGINS.append(f'https://{_render_host}')

# ── BASE DE DATOS: PostgreSQL vía DATABASE_URL ─────────────────────────────
if not os.environ.get('DATABASE_URL'):
    raise ImproperlyConfigured(
        'Falta DATABASE_URL. En Render: Environment → DATABASE_URL '
        '(usar la Internal Database URL de PostgreSQL).'
    )

DATABASES = {
    'default': dj_database_url.config(
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=_bool_env('DB_SSL_REQUIRE', True),
    )
}

# ── HTTPS detrás del proxy de Render ───────────────────────────────────────
# SIN SECURE_PROXY_SSL_HEADER, SECURE_SSL_REDIRECT=True provoca un bucle infinito
# de redirecciones en Render (el proxy habla HTTP con gunicorn).
# FORCE_HTTPS=False permite probar la imagen en local por http://localhost.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

_https = _bool_env('FORCE_HTTPS', True)
SECURE_SSL_REDIRECT = _https
SESSION_COOKIE_SECURE = _https
CSRF_COOKIE_SECURE = _https
SECURE_HSTS_SECONDS = 31536000 if _https else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = _https
SECURE_HSTS_PRELOAD = _https
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'

# allauth: que los enlaces que genere (correos, redirecciones) usen https
ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https' if _https else 'http'

# ── CORREO ─────────────────────────────────────────────────────────────────
# Sin esto, allauth intenta enviar por SMTP a localhost al registrarse o
# recuperar contraseña y la vista truena con ConnectionRefusedError (500).
# Por defecto los correos se imprimen en el log de Render.
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend'
)

# ── ESTÁTICOS (WhiteNoise) ─────────────────────────────────────────────────
# Django ≥ 5.1 ya NO lee STATICFILES_STORAGE; se usa STORAGES.
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}
# Si una plantilla pide un estático que no está en el manifiesto, NO tumbar toda
# la página con error 500: solo ese archivo dará 404.
WHITENOISE_MANIFEST_STRICT = False

# ── LOGGING ────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '[%(levelname)s] %(name)s: %(message)s'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'root': {'handlers': ['console'], 'level': 'WARNING'},
    'loggers': {
        'django.security': {
            'handlers': ['console'], 'level': 'ERROR', 'propagate': False,
        },
    },
}