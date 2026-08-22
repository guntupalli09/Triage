# Step 4A.10 Phase 0 — Frozen Provider Configuration

- Provider: Anthropic (direct Messages API, `https://api.anthropic.com/v1/messages`)
- Model: `claude-haiku-4-5-20251001`
- `anthropic-version`: `2023-06-01`
- `max_tokens`: 1024
- `temperature`: not set (provider default; not overridden in `semantic_discovery_real.py`)
- `system`: see `frozen_semantic_prompt.txt` (SHA-256: `a8988ce24b7a0796850f6f55054312b6659c087cb0edf46e55504c51e4bc7a98`)
- `messages`: single user turn, `"<document>\n{document_text}\n</document>"` — the entire document text is sent, unchunked (see Phase 32 for the privacy implication of this)
- Structured-output/schema configuration: none — plain-text completion instructed (via the system prompt) to return JSON; parsed with a lenient fence-stripping `_extract_json` helper, not the API's native structured-output/tool-use mode
- Timeout: 30s (`_TIMEOUT_SECONDS` in `semantic_discovery_real.py`)
- Retries: none — a single attempt per document; any failure raises and is treated as "provider unavailable" upstream
- Fallback behavior: on any exception, malformed JSON, or non-list `candidates`, the caller (`_run_semantic_discovery` in `indemnification_policy_engine.py`) records the failure and returns `RECOGNITION_UNCERTAIN` if regex also found nothing — never `CONFIRMED_ABSENT` (see Phase 2/23 audit)
- Seed: not supported / not set — the Messages API does not expose a deterministic seed parameter for this model, and none is requested
- Offsets: never trusted from the model — computed locally via exact substring search (`document_text.find(quote)`) on the returned `quote` field only

**API key handling**: read from `ANTHROPIC_API_KEY` environment variable at call
time (`os.environ.get`); never hardcoded, never logged, never written to any
artifact. Verified in Phase 0.9 below.
