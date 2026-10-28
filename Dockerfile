# Dockerfile — ERP Django en Render
# Python 3.12: Django 6.1 requiere >= 3.12 (con 3.11 pip no encuentra django==6.1.x)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Dependencias del sistema (psycopg2-binary no las exige, pero no estorban)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Dependencias Python primero (aprovecha la caché de capas de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Recolectar estáticos con los MISMOS settings que usa producción, para que se
# genere el manifiesto (staticfiles.json) que WhiteNoise necesita en ejecución.
# Las variables van solo en este comando: no quedan guardadas en la imagen.
# Sin "|| echo": si collectstatic falla, el build falla y se ve en el log.
RUN SECRET_KEY=solo-para-build \
    DATABASE_URL=sqlite:////tmp/build.db \
    DB_SSL_REQUIRE=False \
    python manage.py collectstatic --no-input --settings=core.settings_prod

EXPOSE $PORT

# Arranque:
#  1) migrate: en Docker, Render NO ejecuta el buildCommand de render.yaml,
#     así que las migraciones se aplican aquí al iniciar.
#  2) createsuperuser opcional: solo si defines DJANGO_SUPERUSER_USERNAME,
#     DJANGO_SUPERUSER_EMAIL y DJANGO_SUPERUSER_PASSWORD en Render
#     (el plan gratuito no tiene Shell). Si ya existe, se ignora.
#  3) exec gunicorn: gunicorn queda como proceso principal y recibe las señales
#     de apagado de Render. Usa WEB_CONCURRENCY (Render lo fija en 1 por defecto).
CMD ["sh", "-c", "python manage.py migrate --no-input && ( [ -z \"$DJANGO_SUPERUSER_USERNAME\" ] || python manage.py createsuperuser --noinput || true ) && exec gunicorn core.wsgi:application --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY:-2} --timeout 120 --access-logfile - --error-logfile -"]