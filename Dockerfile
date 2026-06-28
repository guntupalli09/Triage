FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd -r triage && useradd -r -g triage -d /app -s /sbin/nologin triage

WORKDIR /app

COPY requirements-docker.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R triage:triage /app

USER triage

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/config || exit 1

CMD ["gunicorn", "main:app", "-c", "gunicorn.conf.py"]
