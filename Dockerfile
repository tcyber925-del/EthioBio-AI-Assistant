# syntax=docker/dockerfile:1
# BUILD_CACHE_BUST=2026-07-18
FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tesseract-ocr \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir uv

RUN uv pip install --system torch --index-url https://download.pytorch.org/whl/cpu

RUN uv pip install --system -r requirements.txt \
    && uv pip uninstall --system torchvision -y \
    && rm -rf /root/.cache/uv

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY . .
RUN find /app -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
RUN echo "BUILD_CACHE_BUST=2026-07-18-2"

EXPOSE 8000

CMD alembic upgrade head && python -m uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}
