# Cloudflare Containers / any Docker host — full FastAPI (Chroma + Deep Reading).
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    ENV=staging \
    SESSION_STORE_BACKEND=memory \
    DEEP_READING_ENABLED=true

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry==2.3.2

COPY pyproject.toml poetry.lock* ./
RUN poetry install --only main --no-root

COPY app ./app

RUN mkdir -p /app/chroma_data \
    && printf '[]\n' > /app/reflections.json \
    && printf '[]\n' > /app/edges.json

EXPOSE 8000

# Long Deep Reading requests need generous timeouts at the edge / container proxy.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "75"]
