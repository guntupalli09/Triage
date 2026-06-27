"""OpenAI call logging: model, tokens, latency, cost."""
from __future__ import annotations

from triage_logging import get_logger

logger = get_logger(__name__)

COST_PER_1K = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
}


def log_llm_call(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
) -> None:
    total = prompt_tokens + completion_tokens
    costs = COST_PER_1K.get(model, {"input": 0.001, "output": 0.002})
    cost = (prompt_tokens / 1000 * costs["input"]) + (completion_tokens / 1000 * costs["output"])
    cost_cents = int(cost * 100)
    logger.llm(
        f"{model} response ({prompt_tokens} in / {completion_tokens} out / "
        f"{latency_ms / 1000:.2f}s / ~{cost_cents}¢)"
    )


def log_llm_fallback(reason: str) -> None:
    logger.llm(f"Using fallback response: {reason}")


def log_llm_error(error: str) -> None:
    logger.error(f"LLM error: {error}")
