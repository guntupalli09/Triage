"""Gunicorn production configuration."""
import os

workers = int(os.getenv("WEB_WORKERS", "4"))
worker_class = "uvicorn.workers.UvicornWorker"
bind = os.getenv("BIND", "0.0.0.0:8000")
timeout = 120
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = "info"
