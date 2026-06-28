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
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# --- Graceful shutdown ---
# 30s grace period for in-flight requests to complete before SIGKILL.
# Allows most OpenAI calls to finish rather than dropping them.
graceful_timeout = 30


def when_ready(server):
    """Run database schema initialization once in the master process
    (after preload_app), before workers are forked, to avoid race conditions."""
    import os
    os.environ["GUNICORN_ARBITER"] = "1"
    from database import init_db
    init_db()
