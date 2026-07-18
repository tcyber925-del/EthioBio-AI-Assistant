web: find /app -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; python -m uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}
