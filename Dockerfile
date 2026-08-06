# ---- Base image ----
FROM python:3.12-slim

# ---- Environment setup ----
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ---- Install OS deps needed for psycopg2 build (binary wheel used, but keep libpq for safety) ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ---- Install Python deps first (better layer caching) ----
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Copy app code ----
COPY app.py .

# ---- Create non-root user (security best practice) ----
RUN useradd -m appuser
USER appuser

EXPOSE 5000

# ---- Healthcheck used by Docker / ECS-style orchestration ----
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# ---- Run with gunicorn (production-ready WSGI server) ----
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
