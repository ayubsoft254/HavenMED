# ─────────────────────────────────────────────────────────────────────────────
# HavenMED — Dockerfile
# Gunicorn WSGI server, non-root user, optimised layer caching
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /deps

# System libs needed to compile Pillow and other C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libjpeg-dev \
        libpng-dev \
        libfreetype6-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY src/requirements.txt .

RUN pip install --upgrade pip \
 && pip wheel --no-cache-dir --wheel-dir /deps/wheels -r requirements.txt


# ── Stage 2: runtime image ───────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Runtime system libs for Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        libpng16-16 \
        libfreetype6 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root application user
RUN groupadd --gid 1001 havenmed \
 && useradd  --uid 1001 --gid havenmed --shell /bin/bash --create-home havenmed

# Install wheels from builder stage (no network access needed)
COPY --from=builder /deps/wheels /tmp/wheels
RUN pip install --no-cache-dir --no-index --find-links /tmp/wheels /tmp/wheels/*.whl \
 && rm -rf /tmp/wheels

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=core.settings

WORKDIR /app

# Copy application source
COPY src/ .

# Persistent data directories — owned by app user
RUN mkdir -p /app/media /app/staticfiles /data \
 && chown -R havenmed:havenmed /app /data

USER havenmed

# Collect static files at build time
RUN python manage.py collectstatic --noinput

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Gunicorn: 3 workers, 120s timeout, logs to stdout
CMD ["gunicorn", \
     "core.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]
