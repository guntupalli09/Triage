"""
Single shared OpenAI provider configuration and low-level transport for
the entire application.

Every code path that calls OpenAI for contract fact discovery/verification
-- fact_admission.py (used by all 12 policy adapters) and
semantic_discovery_real.py (indemnification's discovery step) -- reads its
API key, model, and HTTP transport from this one module. evaluator.py
(findings-explanation generation) and playbook_ai_extraction.py
(AI-assisted playbook import) use the OpenAI SDK client rather than this
module's raw-HTTP transport (a different, pre-existing mechanism for a
different feature), but read their API key and model from the same
get_api_key()/get_model() functions here, so there is exactly one place in
the codebase that knows the OPENAI_API_KEY/OPENAI_MODEL environment
variable names and the default model value.

No adapter, feature, or module should read os.environ.get("OPENAI_API_KEY")
or os.environ.get("OPENAI_MODEL") directly, or hardcode a model literal --
call get_api_key()/get_model() (or, for a raw chat-completion call,
call_chat_completion()) instead.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional

DEFAULT_MODEL = "gpt-4o-mini"
API_URL = "https://api.openai.com/v1/chat/completions"


def get_api_key(explicit: Optional[str] = None) -> Optional[str]:
    """Returns the configured OpenAI API key, or None if unconfigured.
    `explicit` (e.g. a caller-supplied override, mainly used by tests)
    takes precedence over the OPENAI_API_KEY environment variable."""
    key = explicit or os.environ.get("OPENAI_API_KEY")
    return key.strip() if key else None


def get_model(explicit: Optional[str] = None) -> str:
    """Returns the configured OpenAI model. `explicit` takes precedence
    over the OPENAI_MODEL environment variable, which takes precedence
    over DEFAULT_MODEL."""
    return explicit or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)


class OpenAIProviderError(RuntimeError):
    """Raised by call_chat_completion on any failure -- missing key,
    network error, timeout, or non-200 response. Callers must treat this
    as "provider unavailable," never as evidence that a proposition is
    false or a clause is absent; each caller catches this and converts it
    into its own domain-specific unavailable/error state."""


def call_chat_completion(
    system_prompt: str,
    user_prompt: str,
    *,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 1024,
    timeout_seconds: int = 30,
    response_format_json: bool = True,
) -> dict:
    """Raw HTTP POST to the OpenAI Chat Completions API (no SDK
    dependency, matching this application's existing transport). Returns
    the parsed JSON response payload as a dict. Raises
    OpenAIProviderError on any failure; never returns a partial/guessed
    result."""
    key = get_api_key(api_key)
    if not key:
        raise OpenAIProviderError("OPENAI_API_KEY not set")

    body_dict = {
        "model": get_model(model),
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if response_format_json:
        body_dict["response_format"] = {"type": "json_object"}
    body = json.dumps(body_dict).encode("utf-8")

    req = urllib.request.Request(
        API_URL, data=body, method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise OpenAIProviderError(f"request failed: {exc}") from exc
    except (TimeoutError, OSError) as exc:
        raise OpenAIProviderError(f"request failed: {exc}") from exc
