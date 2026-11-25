FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim AS runtime
WORKDIR /app
COPY --from=builder /install /usr/local
RUN useradd --create-home --uid 10001 appuser
COPY app/ ./app/
COPY utils/ ./utils/
ENV PORT=8000 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 CMD python -c "import os,urllib.request; urllib.request.urlopen('http://localhost:'+os.getenv('PORT','8000')+'/health', timeout=2)"
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2 --timeout-graceful-shutdown 5"]