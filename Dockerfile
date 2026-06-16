FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install uv && rm -rf ~/.cache/pip \
    && uv pip install --system torch --index-url https://download.pytorch.org/whl/cpu \
    && uv pip install --system -r requirements.txt \
    && uv pip uninstall --system torchvision -y \
    && python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
