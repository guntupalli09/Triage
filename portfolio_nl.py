"""
Natural-language → validated structured portfolio query.

The LLM is allowed to *translate* a question into the portfolio_query AST.
It is never allowed to answer the question, invent contract facts, or emit
SQL. If translation fails or the AST does not validate, the request is
rejected — we do not fall back to scanning contracts with the model.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional, Tuple

from portfolio_query import (
    PortfolioQueryError,
    StructuredQuery,
    parse_structured_query,
    query_schema,
)
import openai_provider
import prompt_security

logger = logging.getLogger(__name__)

_SYSTEM = """You translate a lawyer's portfolio question into a structured filter query.
You do NOT answer the question. You do NOT invent contracts, numbers, or SQL.
You output a single JSON object with this exact shape:
{"filters":[{"field":"...","op":"...","value":...}],"combinator":"and"}

Allowed fields and operators are provided in the schema. Use only those.
Rules:
- contract_type MSA/Master Services Agreement → {"field":"contract_type","op":"eq","value":"MSA"}
- liability cap above/over/greater than N → {"field":"liability_cap","op":"gt","value":N}
- unlimited liability → {"field":"liability_unlimited","op":"eq","value":true}
- governing law Texas/New York → {"field":"governing_law","op":"contains","value":"..."}
- termination for convenience → {"field":"termination_for_convenience","op":"eq","value":true}
- assignment requires consent → {"field":"assignment_requires_consent","op":"eq","value":true}
- payment terms longer than N days → {"field":"payment_terms_days","op":"gt","value":N}
- mutual indemnification → {"field":"indemnification","op":"eq","value":"mutual"}
- HIGH severity → {"field":"highest_severity","op":"eq","value":"high"}
- unresolved review items → {"field":"has_unresolved","op":"eq","value":true}
- cross-policy interactions → {"field":"has_interactions","op":"eq","value":true}
If the question cannot be expressed with the allowed fields, output:
{"unsupported": true, "reason": "short reason"}
Never include a "sql" key. Never wrap the JSON in markdown."""


class UnsupportedPortfolioQuery(PortfolioQueryError):
    pass


def _sanitize_question(question: str) -> str:
    text = (question or "").strip()
    if not text:
        raise PortfolioQueryError("Question is empty.")
    if len(text) > 500:
        raise PortfolioQueryError("Question is too long (max 500 characters).")
    lowered = text.lower()
    if "select " in lowered and " from " in lowered:
        raise PortfolioQueryError("SQL is not accepted as a portfolio question.")
    # Reuse prompt-injection guards used on contract excerpts. If the
    # question looks like an instruction override, reject rather than send.
    if prompt_security.looks_like_prompt_injection(text):
        raise PortfolioQueryError("Question was rejected by the prompt-security filter.")
    return prompt_security.sanitize_excerpt_for_prompt(text)


def interpret_portfolio_question(
    question: str,
    *,
    api_key: Optional[str] = None,
) -> Tuple[StructuredQuery, Dict[str, Any]]:
    """Returns (validated AST, raw model JSON). Raises PortfolioQueryError
    / UnsupportedPortfolioQuery. Never returns an unvalidated structure."""
    cleaned = _sanitize_question(question)
    schema = query_schema()
    user_content = (
        "SCHEMA:\n"
        + json.dumps(schema, sort_keys=True)
        + "\n\nQUESTION:\n<<<QUESTION_START>>>\n"
        + cleaned
        + "\n<<<QUESTION_END>>>"
    )
    key = openai_provider.get_api_key(api_key)
    if not key:
        raise UnsupportedPortfolioQuery(
            "Natural-language search is unavailable because no LLM provider is configured. "
            "Use structured filters instead."
        )
    try:
        payload = openai_provider.call_chat_completion(
            _SYSTEM,
            user_content,
            api_key=key,
            max_tokens=600,
        )
    except Exception as exc:  # noqa: BLE001 — provider failure must not become an answer
        logger.warning("portfolio NL translation failed: %s", exc)
        raise UnsupportedPortfolioQuery(
            "Natural-language translation failed. Use structured filters instead."
        ) from exc

    try:
        raw = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise UnsupportedPortfolioQuery("Translator returned an unexpected payload.") from exc
    if not raw:
        raise UnsupportedPortfolioQuery("The translator returned an empty response.")
    text = raw if isinstance(raw, str) else json.dumps(raw)
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise UnsupportedPortfolioQuery("Translator did not return valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise UnsupportedPortfolioQuery("Translator returned a non-object JSON value.")
    if "sql" in parsed or "raw_sql" in parsed or "query_sql" in parsed:
        raise PortfolioQueryError("Translator attempted to emit SQL, which is not permitted.")
    if parsed.get("unsupported"):
        reason = str(parsed.get("reason") or "This question cannot be expressed as a structured filter.")
        raise UnsupportedPortfolioQuery(reason)
    query = parse_structured_query({
        "filters": parsed.get("filters") or [],
        "combinator": parsed.get("combinator") or "and",
        "limit": parsed.get("limit", 100),
        "offset": parsed.get("offset", 0),
    })
    return query, parsed
