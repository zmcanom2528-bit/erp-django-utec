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

# Arranque (W16): docker-entrypoint.sh aplica migraciones, inicia el worker de
# Celery embebido (si CELERY_EMBEDDED_WORKER=1 y hay REDIS_URL) y Gunicorn.
# El sed quita finales de línea de Windows (CRLF), que romperían el script.
RUN sed -i 's/\r$//' docker-entrypoint.sh
ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]