# LLM Boundary

TriageCounsel uses a **neural-symbolic architecture**: a deterministic
rule engine detects risks; an LLM (OpenAI) only explains what the
deterministic engine already found. This document specifies exactly where
that boundary is enforced in code, and what has (and has not) changed
about it during the security hardening pass. See also
`docs/llm_layer/llm_role_and_limits.md` and `docs/llm_layer/
hallucination_prevention.md` for the original architectural rationale —
this document is the security-focused companion, current as of the P1–P9
hardening work.

## The Boundary, Precisely

| The LLM... | Enforced how |
|---|---|
| **Never sees full contract text** | `evaluator.LLMEvaluator.evaluate()` raises `ValueError` ("LLM LOCKDOWN VIOLATION") if its `contract_text` parameter is ever non-`None`. No call site in `main.py` passes it. |
| **Never detects new risks** | Only receives pre-computed `findings` (rule_id, title, severity, rationale, matched_excerpt) — it has no contract text to detect anything *in*. |
| **Never changes severities or the overall risk level** | `evaluator.evaluate()` unconditionally overwrites `result["overall_risk"]` with the deterministic value after the API call returns, discarding whatever the model output. |
| **Never invents findings undetected by the rule engine** | `_verify_output_maps_to_findings()` checks every `top_issue` the model returns against the normalized set of rule names/titles/aliases actually sent; an unmapped issue is logged as a warning. (Currently a logged warning, not a hard rejection — see "Known Limitations" below.) |
| **Only ever runs when explicitly invoked, and degrades safely** | If `OPENAI_API_KEY` is unset or the API call fails, `evaluate()` returns `None` / the caller falls back to `create_fallback_response()` — a rules-only summary with no fabricated analysis. The deterministic report is unaffected either way. |

## What Actually Reaches the Prompt

From `evaluator._build_prompt()`, per finding sent to the model:

- `rule_name`, `title`, `severity`, `rationale` — all **fixed strings from
  the rule engine's own rule definitions**, authored by the rules-engine
  maintainers, not derived from contract text. Not attacker-controlled.
- `matched_excerpt` — **the one piece of attacker-controlled text that
  reaches the prompt.** A short snippet of the actual contract, selected
  by the rule engine's pattern match.

Everything else in the contract — the surrounding paragraphs, other
clauses, anything not selected as a matched excerpt for a fired rule — is
never seen by the model at all.

## Hardening Applied to `matched_excerpt` (P6)

Because `matched_excerpt` is the only untrusted input reaching the prompt,
it goes through `prompt_security.py` before being inserted:

1. **Length cap** (300 chars) — bounds how much attacker-controlled text
   can ever be in a single excerpt, independent of what the rule engine
   matched.
2. **Prompt-injection pattern detection** — phrasing like "ignore previous
   instructions", "you are now", "system:"-style role markers. A match
   causes the *entire excerpt* to be withheld and replaced with
   `[excerpt withheld: flagged as a potential prompt-injection attempt]`
   — the suspicious text is never sent to the model at all.
3. **Delimiter escaping** — even excerpts that pass detection can't
   contain the literal `<<<EXCERPT_START>>>`/`<<<EXCERPT_END>>>` markers
   or ``` ``` ``` code-fence sequences that could be used to make injected
   text look like it closes the data section and resumes "outside" it as
   instructions.
4. **Delimiter isolation** — every excerpt is wrapped in explicit
   start/end markers, with prompt-level instructions telling the model
   everything between them is data to analyze, never instructions to
   follow, even if it reads like a command or role change.

## Output Constraints (Prompt-Level, Not Code-Enforced)

The prompt instructs the model to:
- Never declare legality, enforceability, or safety
- Avoid phrases like "safe to sign", "illegal", "enforceable", "you should"
- Prefer hedged language ("may indicate", "commonly negotiated")
- Always include the fixed disclaimer: *"This is automated risk triage,
  not legal advice."*

**These are prompt instructions, not a code-level filter on the model's
output text.** `_validate_result()` only checks for required JSON keys and
correct types — it does not scan `why_it_matters`/`negotiation_
consideration` for the banned phrases and reject/strip them if present.
Compliance with the phrasing constraints depends on the model following
instructions.

## What Would Constitute a Boundary Violation

For anyone reviewing changes to this code: a change violates the LLM
boundary if it does any of the following. Treat these as hard rules, not
style preferences:

- Passes `contract_text` (or any derivative containing more than a
  short rule-matched excerpt) to `LLMEvaluator.evaluate()`
- Lets the LLM's `overall_risk` output reach the database or UI without
  being overwritten by the deterministic value
- Persists `findings_json` from anything other than the rule engine's own
  output
- Removes or weakens the `contract_text is not None` guard in
  `evaluate()`
- Sends `matched_excerpt` to the prompt without going through
  `prompt_security.sanitize_excerpt_for_prompt()`

## Known Limitations

- **`_verify_output_maps_to_findings()` logs, it doesn't block.** An LLM
  output containing a `top_issue` that doesn't map to any real finding is
  currently a warning in the logs, not a rejected/stripped response. A
  hallucinated issue title could theoretically reach the user if the model
  produces one despite the constraints.
- **Output phrasing constraints are prompt-level only** (see above) — no
  code-level post-processing scans for or removes banned phrases if the
  model doesn't comply with the instruction.
- **Injection detection is pattern-based**, not a formal guarantee — see
  `THREAT_MODEL.md` T6 for the accepted residual risk and why the blast
  radius stays bounded regardless (the model still can't alter
  deterministic findings or risk level even if an injection succeeds).
