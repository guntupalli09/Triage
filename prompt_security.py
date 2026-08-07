"""
Prompt injection hardening for evaluator.py's LLM prompt construction (P6).

The deterministic architecture is unchanged by this module: the LLM still
never sees full contract text (evaluator.py's LLM LOCKDOWN guard), never
invents findings, and never overrides the deterministic overall_risk (the
post-call overwrite in evaluator.evaluate()). What this module hardens is
the one piece of attacker-controlled text that DOES reach the LLM prompt —
`matched_excerpt`, a short snippet of the actual contract text the rule
engine matched. Contract authors write that text, not us, so it must be
treated as untrusted input to the prompt, not as part of the instructions.

Four layers, applied in order:
1. Maximum excerpt length — bounds how much attacker-controlled text can
   ever reach the prompt, independent of whatever the rule engine matched.
2. Prompt-injection pattern detection — common jailbreak/override phrasing
   ("ignore previous instructions", "you are now", role markers like
   "system:") causes the excerpt to be withheld entirely rather than sent.
3. Delimiter escaping — even excerpts that pass the detector can't contain
   the literal delimiter markers or code-fence sequences that could be used
   to make injected text look like it closes the data section and resumes
   "outside" it as instructions.
4. Delimiter isolation — every excerpt is wrapped in explicit start/end
   markers, with prompt-level instructions telling the model everything
   between them is untrusted data to analyze, never instructions to follow.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Tighter than the 2000-char "log a warning" threshold evaluator.py already
# has for the whole findings payload — this specifically bounds what a
# single excerpt can contribute to the prompt.
MAX_EXCERPT_CHARS = 300

EXCERPT_START = "<<<EXCERPT_START>>>"
EXCERPT_END = "<<<EXCERPT_END>>>"

REDACTED_PLACEHOLDER = "[excerpt withheld: flagged as a potential prompt-injection attempt]"

_INJECTION_PHRASES = [
    r"ignore (all |any )?(the |your )?(previous|prior|above|earlier) instructions",
    r"disregard (all |any )?(the |your )?(previous|prior|above|earlier)",
    r"forget (all |your )?(previous|prior) (instructions|rules)",
    r"new instructions\s*:",
    r"override (your|the) (instructions|rules|system prompt)",
    r"reveal (your|the) (system )?prompt",
    r"system prompt",
    r"you are now\b",
    r"act as (a|an)\b",
    r"do not follow (your|the) (instructions|rules)",
    r"\bjailbreak\b",
    r"pretend (you are|to be)\b",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PHRASES), re.IGNORECASE)

# A line that looks like a chat-role marker ("system:", "assistant:", ...)
# is a structural attempt to inject a new turn, independent of wording.
_ROLE_MARKER_RE = re.compile(r"(?im)^\s*(system|assistant|user|human|ai)\s*:")


def looks_like_prompt_injection(text: str) -> bool:
    return bool(_INJECTION_RE.search(text) or _ROLE_MARKER_RE.search(text))


def sanitize_excerpt_for_prompt(excerpt: str, *, rule_id: str = "") -> str:
    """Returns text safe to embed in the LLM prompt: truncated, and either
    the (delimiter-escaped) original or a redacted placeholder if it looks
    like an injection attempt. Callers should still wrap the result with
    wrap_excerpt() before inserting it into the prompt."""
    if not excerpt:
        return excerpt

    text = excerpt[:MAX_EXCERPT_CHARS]

    if looks_like_prompt_injection(text):
        logger.warning(
            f"PROMPT INJECTION GUARD: excerpt withheld from LLM prompt "
            f"(rule_id={rule_id!r}, len={len(excerpt)})"
        )
        return REDACTED_PLACEHOLDER

    # Neutralize sequences that could otherwise be used to escape the
    # delimiter wrapper itself, even in text that didn't trip the
    # injection heuristics above.
    text = text.replace(EXCERPT_START, "[marker removed]").replace(EXCERPT_END, "[marker removed]")
    text = text.replace("```", "'''")

    return text


def wrap_excerpt(sanitized_excerpt: str) -> str:
    return f"{EXCERPT_START}{sanitized_excerpt}{EXCERPT_END}"
