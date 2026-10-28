# core/settings_prod.py
"""Configuración de producción — Render.com.

Hereda settings.py. TODO lo sensible sale de variables de entorno:

    DJANGO_SETTINGS_MODULE  → core.settings_prod
    SECRET_KEY              → obligatoria (Render: generateValue)
    DATABASE_URL            → obligatoria (Render: fromDatabase)
    ALLOWED_HOSTS           → opcional, separados por coma
    CSRF_TRUSTED_ORIGINS    → opcional, separados por coma (con https://)
    DB_SSL_REQUIRE          → "True" (default) en Render; "False" en Docker local
    RENDER_EXTERNAL_HOSTNAME→ la inyecta Render automáticamente
"""
import os

import dj_database_url

from .settings import *   # noqa: F401,F403  hereda la configuración base

# ── SEGURIDAD BÁSICA ───────────────────────────────────────────────────────
DEBUG = False
SECRET_KEY = os.environ['SECRET_KEY']   # falla a propósito si no existe


def _lista_env(nombre):
    """Lee una variable de entorno 'a,b,c' y devuelve ['a','b','c']."""
    return [x.strip() for x in os.environ.get(nombre, '').split(',') if x.strip()]


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
DATABASES = {
    'default': dj_database_url.config(
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=os.environ.get('DB_SSL_REQUIRE', 'True') == 'True',
    )
}

# ── HTTPS detrás del proxy de Render ───────────────────────────────────────
# SIN esta línea, SECURE_SSL_REDIRECT=True provoca un bucle infinito de
# redirecciones en Render (el proxy habla HTTP con gunicorn).
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'

# ── ESTÁTICOS (WhiteNoise) ─────────────────────────────────────────────────
# Django ≥ 5.1 ya NO lee STATICFILES_STORAGE; se usa STORAGES.
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

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
