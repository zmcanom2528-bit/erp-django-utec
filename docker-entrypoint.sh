#!/bin/sh
# docker-entrypoint.sh
# Punto de entrada unificado para el contenedor ERP Django.
# Se ejecuta en LOCAL (docker-compose) y en PRODUCCIÓN (Render).
# IMPORTANTE: este archivo debe tener finales de línea LF (ver .gitattributes).
# ─────────────────────────────────────────────────────────────────
set -e   # detener si cualquier comando falla

# ── W16: si se recibe un comando, ejecutarlo tal cual ────────────────
# Ej.: docker-compose `command: celery -A core worker ...` o el
# "Docker Command" de un Background Worker en Render.
# Sin argumentos → flujo normal del servicio web (migrar + gunicorn).
if [ "$#" -gt 0 ]; then
    echo "==> [entrypoint] Ejecutando comando: $*"
    exec "$@"
fi

echo "==> [entrypoint] Ejecutando migraciones de base de datos..."
python manage.py migrate --noinput

echo "==> [entrypoint] Recolectando archivos estáticos..."
python manage.py collectstatic --noinput --clear

echo "==> [entrypoint] Verificando la configuración de Django..."
python manage.py check --deploy 2>/dev/null || python manage.py check

# Superusuario opcional: solo si defines DJANGO_SUPERUSER_USERNAME,
# DJANGO_SUPERUSER_EMAIL y DJANGO_SUPERUSER_PASSWORD en Render (el plan
# gratuito no tiene Shell). Nunca se escriben contraseñas en el código.
# Si el usuario ya existe, se ignora.
if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ]; then
    echo "==> [entrypoint] Verificando superusuario..."
    python manage.py createsuperuser --noinput || true
fi

# ── W16: worker de Celery embebido (opción gratuita de Render) ───────
# Render Free no ofrece Background Workers: el worker corre en segundo
# plano dentro del mismo contenedor que Gunicorn.
#   --pool=solo           → un solo proceso (cabe en 512 MB)
#   --without-gossip/mingle/heartbeat → menos conexiones a Redis
# Se activa con CELERY_EMBEDDED_WORKER=1 y requiere REDIS_URL.
#
# W18: Beat (tareas programadas) también va embebido con --beat, porque
# Render Free no tiene Background Workers. Solo debe existir UN Beat:
# el servicio web debe tener 1 instancia. Se desactiva con
# CELERY_EMBEDDED_BEAT=0. El archivo del schedule va a /tmp (disco efímero).
if [ "${CELERY_EMBEDDED_WORKER:-0}" = "1" ] && [ -n "${REDIS_URL:-}" ]; then
    BEAT_OPTS=""
    if [ "${CELERY_EMBEDDED_BEAT:-1}" = "1" ]; then
        BEAT_OPTS="--beat --schedule=/tmp/celerybeat-schedule"
        echo "==> [entrypoint] Celery Beat embebido ACTIVADO (reporte diario ${REPORTE_DIARIO_HORA:-23:00} hora MX)."
    fi
    echo "==> [entrypoint] Iniciando worker de Celery embebido (cola erp_django)..."
    # shellcheck disable=SC2086
    celery -A core worker \
        --loglevel=info \
        --queues=erp_django \
        --pool=solo \
        --without-gossip --without-mingle --without-heartbeat \
        $BEAT_OPTS &
else
    echo "==> [entrypoint] Worker de Celery embebido DESACTIVADO."
fi

echo "==> [entrypoint] Iniciando Gunicorn en 0.0.0.0:${PORT:-8000}..."
exec gunicorn core.wsgi \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${WEB_CONCURRENCY:-2} \
    --timeout 120 \
    --log-file - \
    --access-logfile -
