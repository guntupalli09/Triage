"""
Core logging infrastructure for Triage.

Provides:
- TriageLogger with custom log levels (ENGINE, RULE, MATCH, SUPPRESS, etc.)
- Dual-mode formatting: pretty (terminal) or JSON (production)
- Correlation ID via contextvars for request tracing
- LogContext context manager for structured fields
"""
from __future__ import annotations

import contextvars
import json
import logging
import os
import random
import string
import sys
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Optional

_analysis_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("analysis_id", default=None)
_log_context_var: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar("log_context", default={})

ENGINE = 25
RULE = 23
MATCH = 24
SUPPRESS = 22
VERIFY = 21
LLM = 26
DATABASE = 22
CACHE = 21
AUDIT = 22
SUCCESS = 25

logging.addLevelName(ENGINE, "ENGINE")
logging.addLevelName(RULE, "RULE")
logging.addLevelName(MATCH, "MATCH")
logging.addLevelName(SUPPRESS, "SUPPRESS")
logging.addLevelName(VERIFY, "VERIFY")
logging.addLevelName(LLM, "LLM")
logging.addLevelName(DATABASE, "DATABASE")
logging.addLevelName(CACHE, "CACHE")
logging.addLevelName(AUDIT, "AUDIT")
logging.addLevelName(SUCCESS, "SUCCESS")

_COLORS = {
    "UPLOAD": "\033[36m",
    "PARSER": "\033[34m",
    "NORMALIZER": "\033[35m",
    "ENGINE": "\033[33m",
    "RULE": "\033[33m",
    "MATCH": "\033[91m",
    "SUPPRESS": "\033[32m",
    "VERIFY": "\033[34m",
    "LLM": "\033[95m",
    "DATABASE": "\033[36m",
    "CACHE": "\033[34m",
    "AUDIT": "\033[90m",
    "SUCCESS": "\033[92m",
    "WARNING": "\033[93m",
    "ERROR": "\033[91m",
    "INFO": "\033[37m",
}
_RESET = "\033[0m"


def generate_analysis_id() -> str:
    now = datetime.utcnow()
    rand = "".join(random.choices(string.digits, k=5))
    return f"TR-{now.strftime('%Y%m%d')}-{rand}"


def set_analysis_id(analysis_id: str) -> None:
    _analysis_id_var.set(analysis_id)


def get_analysis_id() -> Optional[str]:
    return _analysis_id_var.get()


def set_log_context(ctx: Dict[str, Any]) -> None:
    _log_context_var.set(ctx)


def get_log_context() -> Dict[str, Any]:
    return _log_context_var.get()


@contextmanager
def LogContext(**kwargs):
    old = _log_context_var.get()
    merged = {**old, **kwargs}
    token = _log_context_var.set(merged)
    if "analysis_id" in kwargs:
        aid_token = _analysis_id_var.set(kwargs["analysis_id"])
    else:
        aid_token = None
    try:
        yield
    finally:
        _log_context_var.reset(token)
        if aid_token is not None:
            _analysis_id_var.reset(aid_token)


class PrettyFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        level = record.levelname
        prefix = getattr(record, "triage_prefix", level)
        color = _COLORS.get(prefix, _COLORS.get(level, ""))
        aid = _analysis_id_var.get()
        aid_str = f" [{aid}]" if aid else ""
        msg = record.getMessage()
        return f"{color}[{prefix:<12}]{_RESET}{aid_str} {msg}"


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "prefix": getattr(record, "triage_prefix", record.levelname),
            "message": record.getMessage(),
            "logger": record.name,
        }
        aid = _analysis_id_var.get()
        if aid:
            data["analysis_id"] = aid
        ctx = _log_context_var.get()
        if ctx:
            data["context"] = ctx
        if record.exc_info and record.exc_info[1]:
            data["exception"] = str(record.exc_info[1])
        return json.dumps(data)


class TriageLogger(logging.Logger):
    def engine(self, msg, *args, **kwargs):
        kwargs.setdefault("extra", {})["triage_prefix"] = "ENGINE"
        self.log(ENGINE, msg, *args, **kwargs)

    def rule(self, msg, *args, **kwargs):
        kwargs.setdefault("extra", {})["triage_prefix"] = "RULE"
        self.log(RULE, msg, *args, **kwargs)

    def match(self, msg, *args, **kwargs):
        kwargs.setdefault("extra", {})["triage_prefix"] = "MATCH"
        self.log(MATCH, msg, *args, **kwargs)

    def suppress(self, msg, *args, **kwargs):
        kwargs.setdefault("extra", {})["triage_prefix"] = "SUPPRESS"
        self.log(SUPPRESS, msg, *args, **kwargs)

    def verify(self, msg, *args, **kwargs):
        kwargs.setdefault("extra", {})["triage_prefix"] = "VERIFY"
        self.log(VERIFY, msg, *args, **kwargs)

    def llm(self, msg, *args, **kwargs):
        kwargs.setdefault("extra", {})["triage_prefix"] = "LLM"
        self.log(LLM, msg, *args, **kwargs)

    def database(self, msg, *args, **kwargs):
        kwargs.setdefault("extra", {})["triage_prefix"] = "DATABASE"
        self.log(DATABASE, msg, *args, **kwargs)

    def cache(self, msg, *args, **kwargs):
        kwargs.setdefault("extra", {})["triage_prefix"] = "CACHE"
        self.log(CACHE, msg, *args, **kwargs)

    def audit(self, msg, *args, **kwargs):
        kwargs.setdefault("extra", {})["triage_prefix"] = "AUDIT"
        self.log(AUDIT, msg, *args, **kwargs)

    def success(self, msg, *args, **kwargs):
        kwargs.setdefault("extra", {})["triage_prefix"] = "SUCCESS"
        self.log(SUCCESS, msg, *args, **kwargs)

    def upload(self, msg, *args, **kwargs):
        kwargs.setdefault("extra", {})["triage_prefix"] = "UPLOAD"
        self.log(logging.INFO, msg, *args, **kwargs)

    def parser(self, msg, *args, **kwargs):
        kwargs.setdefault("extra", {})["triage_prefix"] = "PARSER"
        self.log(logging.INFO, msg, *args, **kwargs)


logging.setLoggerClass(TriageLogger)


def setup_logging(level: int = logging.INFO) -> None:
    log_format = os.getenv("LOG_FORMAT", "pretty")
    handler = logging.StreamHandler(sys.stdout)
    if log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(PrettyFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> TriageLogger:
    return logging.getLogger(name)  # type: ignore
