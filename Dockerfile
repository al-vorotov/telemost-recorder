FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY shared ./shared
COPY providers ./providers
COPY services ./services

RUN pip install --no-cache-dir -e ".[gateway,tg-bot,transcriber,meeting-worker]"

# meeting_worker subprocess (Playwright / Telemost)
RUN playwright install chromium
RUN playwright install-deps chromium || true

ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/app/data

VOLUME ["/app/data"]
