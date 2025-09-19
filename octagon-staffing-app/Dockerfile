# syntax=docker/dockerfile:1.7

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && rm -rf /var/lib/apt/lists/*


FROM base AS builder

COPY requirements.txt ./
RUN pip install --upgrade pip && pip wheel --no-cache-dir --no-deps -r requirements.txt -w /wheels


FROM base AS runner

ENV PORT=8080 \
    ENVIRONMENT=prod

COPY --from=builder /wheels /wheels
COPY --from=builder /usr/local/bin /usr/local/bin
RUN pip install --no-cache-dir /wheels/*

# Add non-root user
RUN useradd -m -u 10001 appuser
USER appuser

WORKDIR /app
COPY app ./app

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

CMD uvicorn app.main:app --host 0.0.0.0 --port 8080



