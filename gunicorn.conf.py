# Gunicorn configuration for production
# Target: Hetzner CX23 (2 vCPU, 4 GB RAM)
# App: FastAPI with long-running OpenAI API calls

import multiprocessing
import os

# Bind to all interfaces inside Docker container
bind = "0.0.0.0:8000"

# --- Workers ---
# 2 vCPU: use 2 workers instead of the (2*CPU)+1 formula.
# Each uvicorn worker uses ~150-200MB RSS. With 2 workers + postgres + redis,
# we stay well under 4GB. More workers would cause memory pressure and swapping.
workers = int(os.environ.get("WEB_WORKERS", 2))

# UvicornWorker for async FastAPI — required for async endpoints and
# non-blocking I/O during OpenAI API calls.
worker_class = "uvicorn.workers.UvicornWorker"

# No threads needed — UvicornWorker handles concurrency via asyncio event loop.
# Threads would add overhead without benefit for async workers.
threads = 1

# --- Timeouts ---
# 120s accommodates long OpenAI API calls on large contracts.
# Default 30s would kill workers mid-analysis and return 502 to users.
timeout = 120

# 5s keepalive matches typical reverse proxy defaults (nginx default: 75s).
# Keeps connections alive for sequential requests from the same client
# without holding sockets open too long on a small server.
keepalive = 5

# --- Memory leak protection ---
# Recycle workers after 500 requests to prevent gradual memory growth
# from document parsing (PyPDF2, python-docx) and OpenAI client objects.
max_requests = 500

# Random jitter prevents all workers from restarting simultaneously,
# which would cause a brief outage. Range: [500, 550].
max_requests_jitter = 50

# --- Preload ---
# Load app code before forking workers. Saves ~50MB shared memory via
# copy-on-write and catches import errors at startup instead of per-worker.
preload_app = True

# --- Process naming ---
proc_name = "triage-web"

# --- Logging ---
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(t)s "%(r)s" %(s)s %(b)s %(D)sµs %({x-request-id}o)s'

# --- Graceful shutdown ---
graceful_timeout = 30


# --- Hooks ---
def on_starting(server):
    import time
    import logging
    _logger = logging.getLogger("gunicorn.error")
    start = time.monotonic()

    from database import wait_for_db, wait_for_redis, init_db
    _logger.info("Waiting for PostgreSQL...")
    wait_for_db()
    _logger.info("Waiting for Redis...")
    wait_for_redis()
    _logger.info("Running database schema initialization...")
    init_db()
    elapsed = time.monotonic() - start
    _logger.info(f"Startup initialization complete in {elapsed:.2f}s")


def post_fork(server, worker):
    import logging
    logging.getLogger("gunicorn.error").info(f"Worker spawned: pid={worker.pid}")


def worker_exit(server, worker):
    import logging
    logging.getLogger("gunicorn.error").info(f"Worker exiting: pid={worker.pid}")
