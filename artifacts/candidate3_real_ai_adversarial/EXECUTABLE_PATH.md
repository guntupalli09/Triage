# Candidate 3 — Executable Architecture Trace (all 12 adapters)

Traced directly from the current code at commit `4c77577`, not carried
over from any prior report. 11 of 12 adapters share one uniform framework
(`fact_admission.py`); indemnification uses a structurally different but
equally safe mechanism, documented separately and in full in
`PRE_RUN_MANIFEST.md` §4.

## Shared framework (liability, confidentiality, payment_terms,
## ip_ownership, insurance, data_security, governing_law, termination,
## warranties, sla, assignment)

Each of these 11 adapter files, inside its own `_run_semantic_discovery()`
helper, executes the identical sequence:

```
raw_candidates = fact_admission.discover_candidate_spans(text, "<adapter>", <ADAPTER>_SEMANTIC_FOCUS)
verified = [fact_admission.verify_and_ground(c, text, <ADAPTER>_SEMANTIC_PROPOSITION) for c in raw_candidates]
admitted = [c for c in verified if c.admission_status == ADMITTED]
```

| Field | Value (uniform across these 11) |
|---|---|
| AI CALL SITE | `fact_admission.py:_call_model` (line 362) via `discover_candidate_spans` (line 436) and `verify_candidate_proposition` (line 551, called inside `verify_and_ground`, line 953) |
| AI MODEL | `gpt-4o-mini`, `fact_admission._MODEL` |
| CANDIDATE SCHEMA | `fact_admission.CandidateMaterialFact` — no field for a policy-decision state (Hard Rule 1) |
| VERBATIM GROUNDING | `discover_candidate_spans`: `document_text.find(quote)`, discarded on `-1` (line 460-462). `verify_and_ground` → `ground_evidence_quote` (line 628): independent exact-substring re-check of the verifier's own evidence quote |
| OPERATIVE-CONTEXT CHECK | Two independent layers: (a) the adversarial verifier prompt (`_VERIFY_SYSTEM_PROMPT`) is explicitly instructed to search for descriptive/recital/hypothetical/quoted/negated framing before concluding ESTABLISHED; (b) each adapter's OWN deterministic `is_operative_context()`-style gates (where wired) independently constrain what the deterministic side of the Facts object can ever show, regardless of what the AI concludes |
| PARTY/ROLE GROUNDING | Not part of `fact_admission`'s own schema — established by each adapter's deterministic party/role attribution code, run on the (already grounded) evidence span, never trusted from the AI's own claim of which party is obligated |
| CONDITION HANDLING | `ground_qualifiers()` independently grounds `condition_quote`; `evaluate_admission` blocks admission outright if it fails grounding (never dropped silently) |
| EXCEPTION/CARVE-OUT HANDLING | Same mechanism, `exception_quote` |
| DEFINITION HANDLING | `resolve_definition()` (line 690) must reach `RESOLVED` or admission is blocked (line 887-895) |
| CROSS-REFERENCE HANDLING | `resolve_cross_reference_target()` (line 745), same RESOLVED-or-blocked gate |
| COMPETING-READING HANDLING | `ground_competing_readings()` (line 802); 2+ independently-grounded competing readings block admission outright (line 907-917) |
| ABSENCE HANDLING | `absence_state` on the Facts dataclass: `CONFIRMED_ABSENT` (regex found nothing AND semantic discovery ran and found nothing) vs. `RECOGNITION_UNCERTAIN` (semantic discovery errored/unavailable) — never collapsed into each other |
| PROVIDER-FAILURE HANDLING | Any `ProviderUnavailable` from `_call_model` → caught in the adapter's `_run_semantic_discovery` → `absence_state="RECOGNITION_UNCERTAIN"` with `semantic_discovery_error` set → adapter's own `evaluate_*_policy` routes `RECOGNITION_UNCERTAIN` to `REQUIRES_REVIEW`, never `ACCEPT`/`CLEAN`/`CONFIRMED_ABSENT` |
| ADMITTED FACT TYPE | Only `admission_status == "ADMITTED"` candidates are merged onto the Facts object's `ai_identified_condition` / `ai_identified_exception` / `ai_identified_definition_or_reference` fields (and, for insurance/sla/confidentiality, the coverage/uptime/obligation fields directly) |
| DETERMINISTIC EVALUATOR | The adapter's own `evaluate_<adapter>_policy()` in `policy_engine_core.py`'s shared vocabulary |
| FINAL DECISION STATES | `ACCEPT` / `ACCEPT_WITH_NOTE` / `NEGOTIATE` / `MUST_REDLINE` / `PROHIBITED` / `ESCALATE` / `REQUIRES_REVIEW` / `NOT_APPLICABLE` — assigned ONLY inside `evaluate_<adapter>_policy()`, never inside `fact_admission.py` (which has no import of, or reference to, any of these constants) |

**Invariant check (11 adapters):** `fact_admission.py` never imports
`policy_engine_core`'s decision-state constants, and its only output
vocabulary is `ESTABLISHED`/`NOT_ESTABLISHED`/`AMBIGUOUS`/
`INSUFFICIENT_CONTEXT`/`CONFLICTING`/`DEPENDENCY_UNRESOLVED`/
`VERIFICATION_ERROR` plus `ADMITTED`/`NOT_ADMITTED`. Confirmed by direct
`grep` of `fact_admission.py` for any of the 8 decision-state names: zero
matches. **AI output cannot directly set any of the 8 states for these 11
adapters.**

## indemnification (structurally different mechanism)

| Field | Value |
|---|---|
| AI CALL SITE | `semantic_discovery_real.py` (primary discovery, when `SEMANTIC_PROVIDER="REAL"`); `fact_admission.py` (secondary reconciliation channel, when `INDEMNIFICATION_RECONCILIATION_ENABLED`) |
| AI MODEL | `gpt-4o-mini` on both paths |
| CANDIDATE SCHEMA | Primary: `semantic_discovery.DiscoveryCandidate` (no policy-decision field, no party/cap/multiplier field — `semantic_discovery_real.py`'s own Hard Rule 1) |
| VERBATIM GROUNDING | Primary: `document_text.find(quote)` in `discover_candidate_spans_real` (identical mechanism to the shared framework) |
| OPERATIVE-CONTEXT CHECK | Primary: the AI-discovered SPAN is fed into indemnification's own pre-existing deterministic structuring code — the SAME code that parses a regex-discovered span — so operative-context, negation, and role attribution are decided by the SAME deterministic machinery regardless of discovery source |
| PARTY/ROLE GROUNDING | Deterministic structuring code (unchanged whether the span came from regex or AI) |
| CONDITION/EXCEPTION HANDLING | Deterministic structuring code (`detect_condition_in_span`, `detect_conflicting_backward_conditions`, `detect_backward_referenced_qualifier`, etc.) — the secondary reconciliation channel (when enabled) additionally re-checks each obligation's own window via `fact_admission.verify_and_ground`, merging any ESTABLISHED-but-previously-unmodeled condition via `_merge_condition_evidence`, never overriding an already-found one |
| DEFINITION/CROSS-REFERENCE HANDLING | Deterministic structuring code for the primary path; `fact_admission.resolve_definition`/`resolve_cross_reference_target` for the secondary reconciliation channel |
| COMPETING-READING HANDLING | Secondary reconciliation channel only (`fact_admission.ground_competing_readings`) |
| ABSENCE HANDLING | Same `CONFIRMED_ABSENT` vs `RECOGNITION_UNCERTAIN` distinction, tracked via `_run_semantic_discovery`'s own try/except (line 2757-2770) |
| PROVIDER-FAILURE HANDLING | Any exception from `_discover_candidate_spans` is caught broadly (line 2766, `except Exception`) and converted to `([], "<error>")`, never propagated as a crash and never silently treated as "confirmed no obligation" |
| ADMITTED FACT TYPE | Primary: a structured `IndemnityObligation` (party/trigger/monetary/condition), same schema whether AI- or regex-sourced. Secondary: same `ai_identified_condition`-style merge as the other 11 |
| DETERMINISTIC EVALUATOR | `evaluate_indemnification_policy()` |
| FINAL DECISION STATES | Same 8-state vocabulary, assigned only inside `evaluate_indemnification_policy()` |

**Invariant check (indemnification):** the AI-discovered span never
carries a party, trigger, monetary, or condition value of its own — those
are computed by the same deterministic parser that runs on a regex span.
**AI output cannot directly set any of the 8 decision states.**

## Overall Section 1 conclusion

For all 12 adapters, AI may propose (a grounded text span, and, for the
shared-framework 11, an adversarial verification of a specific
proposition). Only deterministic code — `evaluate_admission()` for the
shared framework, indemnification's own structuring code for the primary
path — ever admits a fact as authoritative, and only each adapter's own
`evaluate_<adapter>_policy()` ever assigns a `PolicyDecision.state`. No
STOP condition triggered.
