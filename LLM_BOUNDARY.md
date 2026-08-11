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

## Phase 3 — AI-Assisted Prose Playbook Import (playbook_ai_extraction.py)

A second, separate LLM boundary, distinct from the one above and
reviewed on its own terms rather than folded into it — see
docs/architecture/playbook_authoring_ux_design.md §5.3 for why. The two
boundaries protect different things and are not interchangeable:

|  | Contract-review LLM (`evaluator.py`) | Playbook-import LLM (`playbook_ai_extraction.py`) |
|---|---|---|
| Input | A short, rule-selected `matched_excerpt` (never full contract text) | A deterministically-discovered section of an uploaded playbook document (never a full contract) |
| Job | Explain a pre-detected finding | Propose a structured field value from prose |
| Output authority | Explanatory text only; `overall_risk` always overwritten | Never authoritative at all — see the trust boundary below |
| Enabled by default | Yes (if `OPENAI_API_KEY` set) | **No** — `AI_ASSISTED_IMPORT_ENABLED` env var, off unless explicitly set |
| Per-use consent | Not applicable (not user-initiated per-document) | Required on every import — a checkbox, enforced server-side |

**The hard trust boundary**, enforced entirely in code, not by prompt
wording alone:

```
source document -> LLM candidate -> schema validation ->
evidence verification -> proposal -> lawyer confirmation ->
approval -> activation
```

There is no function in this codebase that writes an LLM-derived value
directly into `PolicyPosition.config_json` (the only thing
`build_*_policy_rule()` ever reads) without first passing through
`playbook_ai_extraction.verify_and_classify_candidate()`, and even a
candidate that reaches `ESTABLISHED` status there is still just a DRAFT
`PolicyPositionField` — the same Phase 1 lifecycle gate
(`validate_position_for_activation`) that blocks every other
authoring path from reaching ACTIVE applies identically here, with zero
special-casing for AI-sourced fields.

**Evidence verification, not trust.** Every candidate's `quote` is
independently verified as a real, whitespace-normalized substring of the
source text actually sent to the model — the model's own reproduction of
the quote is discarded either way; only the located original-document
text is ever stored as evidence. An unverifiable quote is
`NOT_ESTABLISHED`, full stop.

**Quantitative grounding.** A candidate the model tags `basis:
"EXTRACTED"` for a numeric field additionally requires the claimed number
to be textually present in the verified quote (digit or common
word-number) — a model that claims direct extraction of a number its own
quote doesn't contain is downgraded to `REQUIRES_LAWYER_INTERPRETATION`,
never `ESTABLISHED`. This is the specific, tested defense against
"unsupported quantitative invention."

**`basis: "INFERRED"` never reaches `ESTABLISHED`, unconditionally.** If
the model itself reports a candidate as an interpretation rather than a
direct statement, that self-report is honored as a hard ceiling — no
downstream grounding check can promote it back to `ESTABLISHED`.

**Minimizing exposure.** `discover_relevant_sections()` reuses each
policy engine's own anchor regex (`_ANCHOR_RE`, imported directly, never
modified) to find candidate windows per clause type before any model call
— only clause types the document actually appears to address are ever
sent, and only the discovered window, not the whole document.

**Prompt-injection handling — two independent layers.** (1) Every
discovered section is checked with the existing
`prompt_security.looks_like_prompt_injection()` before it is ever placed
in a prompt; a flagged section's text is withheld entirely (never sent),
mirroring `evaluator.py`'s own excerpt-redaction discipline. (2) Even if
a section is not flagged, or a compromised/successfully-injected model
complies with attacker instructions embedded in the document, the
evidence-verification and quantitative-grounding gates above still apply
unconditionally — a boolean/categorical field is exactly as constrained
as any other AI-sourced field, and nothing reaches `ACTIVE` without a
human action regardless. See `benchmarks/phase3_ai_extraction_corpus.py`
for adversarial cases exercising both layers directly (a scripted
"compromised" client that returns a schema-valid, quote-verified
malicious candidate — the second layer alone still keeps it out of
`ESTABLISHED` for boolean/categorical fields via the same self-reported-
`INFERRED`-never-promoted rule, and layer one keeps it from ever reaching
the model in the tested injection cases since the source text itself
trips the detector).

**Schema validation is reused, not reimplemented.** `candidate_schema_for()`
and `verify_and_classify_candidate()` both call directly into Phase 0.1's
`playbook_authoring._validate_field()` / `_is_optional()` /
`_non_none_arm()` / `_BOUNDED_VOCABULARIES` — there is no parallel,
possibly-more-permissive validator for AI output. An unknown clause type,
unknown field, wrong type, or invalid categorical value is rejected by
the exact same code path that rejects a malformed manual-entry form
submission in Phase 1.

**No lawyer-facing confidence score**, consistent with the rest of this
project: the model's internal confidence (if a provider even exposes one)
is never read, stored, or displayed. Only the four categorical statuses
(`ESTABLISHED` / `NOT_ESTABLISHED` / `CONFLICTING` /
`REQUIRES_LAWYER_INTERPRETATION`) and provenance (`EXTRACTED` /
`INFERRED` / `MANUAL`) ever reach the UI.

### Known Limitations (Phase 3)

- **Prompt-level injection resistance is not independently verifiable in
  this environment** — no live model was tested against the adversarial
  corpus (no network access in this development environment); what is
  tested and proven is that the verification pipeline itself blocks a
  maximally-compromised/hallucinating model's output from ever reaching
  `ESTABLISHED` for the field types that matter most. Real-provider
  prompt-injection robustness should be periodically re-verified against
  a live model as providers change.
- **Server-level disable switch only** — there is no organization/tenant
  hierarchy in this codebase to attach an org-level switch to (see
  `docs/architecture/playbook_authoring_ux_design.md`'s explicit scope
  note that a real permission/role model is a separate design pass); the
  implemented switch (`AI_ASSISTED_IMPORT_ENABLED`) is server-wide, which
  is the correct and complete implementation of "organization/server-
  level" for a codebase with no organization concept, but should be
  revisited if a multi-tenant/org model is added later.
- **LLM raw output is not required or expected to be deterministic** —
  by design (see the Phase 3 report). What is deterministic and tested is
  the authoritative boundary: the same verified candidate always produces
  the same stored `PolicyPositionField` state, and nothing probabilistic
  ever becomes authoritative without a human confirmation step.
