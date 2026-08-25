# Real-AI Architecture — Executable Path (Candidate 2, commit dc11333)

Answers to Mission Section 1 (A–J), from direct inspection of the CURRENT
code on `claude/final-trust-architecture-cutover` — nothing here is
carried over from a prior report.

## A. Which function invokes the real AI provider?

`fact_admission.py:362` — `_call_model(system_prompt, user_prompt, *,
api_key)`. It is the SOLE network-call site in the entire codebase for
this architecture; every adapter-facing entry point
(`discover_candidate_spans` at line 436, `verify_candidate_proposition` at
line 551) routes through it. No adapter file makes its own HTTP call.

## B. Which model/provider is used?

**Provider: Anthropic.** `_API_URL = "https://api.anthropic.com/v1/messages"`
(`fact_admission.py:329`). **Model: `claude-haiku-4-5-20251001`**
(`fact_admission.py:330`, the `_MODEL` constant, sent verbatim in the
request body). Auth is a `x-api-key` header (`fact_admission.py:377`),
Anthropic's native Messages API auth scheme — not an OpenAI-compatible
`Authorization: Bearer` header, and not routed through any OpenAI SDK or
endpoint anywhere in this codebase.

**There is no OpenAI (or any other provider) integration anywhere in this
repository.** Confirmed by inspecting every call site in
`fact_admission.py` (the only file that imports `urllib.request` for a
provider call) — grep for `openai`, `OPENAI`, `chat.completions`, or any
non-Anthropic base URL across the repo returns nothing relevant to this
architecture.

## C. What environment/configuration enables it?

`_call_model` reads `os.environ.get("ANTHROPIC_API_KEY")`
(`fact_admission.py:363`) if no `api_key` kwarg is passed (no caller in
the adapter layer passes one — they all rely on the environment variable).
Separately, EACH adapter's own semantic-discovery pathway is gated by
`semantic_discovery_enabled(adapter_env_var)` (`fact_admission.py:134`):
the adapter-specific env var (e.g. `INSURANCE_SEMANTIC_DISCOVERY_ENABLED`)
wins if set at all; otherwise the global `FACT_ADMISSION_MODE=enforced`
switch applies. Both gates must be satisfied — `FACT_ADMISSION_MODE=
enforced` (or an adapter-specific override) to even attempt discovery, AND
`ANTHROPIC_API_KEY` set for `_call_model` to succeed rather than raise
`ProviderUnavailable`.

## D. Does FACT_ADMISSION_MODE control this path?

Yes, exactly as above — it is the global enablement switch each adapter's
own `<ADAPTER>_SEMANTIC_DISCOVERY_ENABLED` module constant reads at import
time (per-adapter `_run_semantic_discovery` helpers, e.g.
`insurance_policy_engine.py`'s `INSURANCE_SEMANTIC_DISCOVERY_ENABLED`
constant). It does not affect `POLICY_ENFORCEMENT_MODE`, which is a
separate switch controlling whether the 12-adapter engine's decisions are
customer-authoritative at all (shadow/legacy vs. cutover) — see Mission
A's `EXECUTABLE_ARCHITECTURE.md`.

## E. Is the real provider reachable for all 12 adapters?

Architecturally yes — every adapter's semantic-discovery helper calls the
same shared `discover_candidate_spans`/`verify_and_ground` functions in
`fact_admission.py`, so there is exactly one network code path shared by
all 12, not 12 separate integrations. Whether it is reachable IN THIS TEST
RUN depends entirely on `ANTHROPIC_API_KEY` being set to a valid Anthropic
key — see the BLOCKED finding below.

## F. Does each adapter actually consume the resulting admitted facts?

Yes — each adapter's `extract_*_facts()` function calls its own
`_run_semantic_discovery()` helper, filters to `admission_status ==
ADMITTED`, and merges the admitted candidates' `condition`/`exception`/
`cross_reference`/`definition_or_reference` fields onto the deterministic
Facts object (e.g. `insurance_policy_engine.py`'s composition at the end
of `extract_insurance_facts`, `confidentiality_policy_engine.py`'s
identical pattern noted in its own comments, and so on for all 12).
Nothing outside `admission_status == ADMITTED` ever reaches the Facts
object.

## G. Where is AI output stripped of authority?

`fact_admission.py`'s module docstring, Hard Rule 1 (line 38): "Nothing in
this module may return, compute, or imply an authoritative POLICY
decision... This module's only output vocabulary is fact-admission states
... plus ADMITTED/NOT_ADMITTED." Enforced structurally: the module never
imports `policy_engine_core`'s decision-state constants (ACCEPT/NEGOTIATE/
etc.), and `assert_authority_boundary_intact()` (line 312) exists as a
runtime self-check of this invariant. The actual authority-stripping
mechanism is `evaluate_admission()` (line 823): even an ESTABLISHED
verification with grounded evidence is only a candidate; it becomes
`ADMITTED` (i.e., eligible to be merged into the adapter's Facts object)
only after passing every gate in that function, and even then, an adapter's
`evaluate_*_policy()` function is the ONLY place a `PolicyDecision.state`
is ever assigned — never `fact_admission.py`.

## H. Where is evidence independently grounded?

`ground_evidence_quote()` (line 628) — re-locates the verifier's claimed
evidence quote via exact substring search against the real document text,
independent of the model. A quote that isn't found character-for-character
fails grounding unconditionally (Hard Rule 2, line 47), regardless of what
the verifier asserted. `ground_qualifiers()` (line 673) does the same for
every condition/exception/cross-reference the verifier claims to have
found, individually.

## I. Where are conditions/exceptions/definitions/cross-references/
competing readings/polarity/operative-status preserved and verified?

- **Conditions/exceptions/cross-references**: `ground_qualifiers()` (line
  673) grounds each independently; `evaluate_admission()` blocks admission
  outright if any claimed qualifier fails grounding (line 919-929) —
  never silently dropped to let the base proposition through clean.
- **Definitions**: `resolve_definition()` (line 690) — must reach status
  `RESOLVED` or admission is blocked (line 887-895).
- **Cross-reference targets**: `resolve_cross_reference_target()` (line
  745) — same RESOLVED-or-blocked gate (line 897-905).
- **Competing readings**: `ground_competing_readings()` (line 802); if 2+
  independently-grounded competing readings exist, admission is blocked
  outright (line 907-917), never resolved by picking one.
- **Polarity/negation and operative status**: NOT part of
  `fact_admission.py`'s own schema — these are established by each
  adapter's OWN deterministic extraction (e.g.
  `policy_engine_core.is_operative_context()`, per-adapter negation
  regexes) BEFORE a candidate is merged in, and by the verifier's
  adversarial prompt design (it is asked to actively try to disprove
  ESTABLISHED status, not confirm it) — but the deterministic layer, not
  the model, is what actually calls a fact "negated" or "non-operative".

## J. Failure-mode handling

All of the following raise or resolve to `ProviderUnavailable` /
`VERIFICATION_ERROR`, which `evaluate_admission()` unconditionally maps to
`NOT_ADMITTED` (Hard Rule 4, line 54) — never `NOT_ESTABLISHED` (which
would mean "confirmed absent"):

- **Timeout**: `TimeoutError`/`OSError` caught at line 389 →
  `ProviderUnavailable`.
- **Network failure**: `urllib.error.URLError` at line 386 →
  `ProviderUnavailable`.
- **Malformed JSON**: `_extract_json` raising `json.JSONDecodeError` at
  line 403 → `ProviderUnavailable`.
- **Empty response / unexpected shape**: checked at line 396
  (`payload.get("content")` must be a list) → `ProviderUnavailable`.
- **Hallucinated quote**: `ground_evidence_quote()` — an ungrounded quote
  fails the grounding gate in `evaluate_admission()` regardless of the
  verifier's claimed status → `NOT_ADMITTED`.
- **Unsupported qualifier**: `ground_qualifiers()` — a condition/exception/
  cross-reference the verifier claims but which cannot be grounded blocks
  admission outright (line 919-929), not silently dropped.
- **Conflicting interpretation**: 2+ grounded competing readings block
  admission (line 907-917); `verify_candidate_proposition` can also itself
  return `CONFLICTING`, one of the `_UNSAFE_VERIFICATION_STATES` (line
  110-113) that `evaluate_admission` rejects outright.

## Critical finding — blocks Phase 2/3 of this mission

`_call_model` (line 362-363) reads **only** `ANTHROPIC_API_KEY`. There is
no code path anywhere in this repository that reads `OPENAI_API_KEY` or
calls any OpenAI endpoint. The credential provided for this mission is an
OpenAI key (`sk-proj-...`), which the existing application has no
mechanism to consume. Per the mission's own instruction ("Use it ONLY
through the existing application's environment/provider configuration")
and its explicit prohibition on substituting mocks or working around a
missing provider, this is reported as a blocker in
`REAL_AI_ARCHITECTURE_REPORT.md` rather than worked around by writing a
new OpenAI client — that would be an unrequested architecture change, not
an exercise of the existing one.
