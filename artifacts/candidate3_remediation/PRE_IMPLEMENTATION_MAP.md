# Candidate 3 Remediation — Pre-Implementation Map

Re-verified directly against current code on `claude/final-trust-architecture-cutover` at commit `59a258a`, not carried over from the prior report. Where the prior report's framing needed correction, that correction is called out explicitly.

## Root Cause 2 (AI-only-on-zero-anchors) — CONFIRMED, uniform across all 12 adapters

Direct grep of every adapter's `extract_*_facts()` confirms the identical gate:

| Adapter | Gate condition (verbatim) | Line |
|---|---|---|
| limitation_of_liability | `if not accepted_anchors:` | liability_policy_engine.py:1703 |
| indemnification | unconditional — `HYBRID_DISCOVERY_ENABLED` runs `_discover_candidate_spans` on every call regardless of deterministic anchor state | indemnification_policy_engine.py:2762-2770 |
| confidentiality | `if not anchors:` | confidentiality_policy_engine.py:303 |
| payment_terms | `if not matches:` | payment_terms_policy_engine.py:721 |
| ip_ownership | `if not matches:` | ip_ownership_policy_engine.py:514 |
| insurance | `if not matches:` | insurance_policy_engine.py:366 |
| data_security | `if not anchors:` | data_security_policy_engine.py:580 |
| governing_law | `if not anchors:` | governing_law_policy_engine.py:179 |
| termination | `if not anchors:` | termination_policy_engine.py:455 |
| warranties | `if not anchors:` | warranties_policy_engine.py:458 |
| sla | `if not anchors:` | sla_policy_engine.py:459 |
| assignment | `if not anchors:` | assignment_policy_engine.py:229 |

**Confirmed: 11 of 12 adapters gate semantic discovery behind "deterministic anchor discovery found zero matches." Indemnification is the sole exception** — this is the correct, narrower framing (indemnification's exceptionalism is a Root-Cause-2 difference, not, as clarified below, a Root-Cause-1 difference).

## Root Cause 1 (admitted AI candidate doesn't become the primary fact) — CONFIRMED, but the prior report's mechanism was imprecise

**Correction to the prior report:** it is not accurate that AI admission "only ever feeds supplementary fields" for 11 of 12 adapters. Direct code reading shows ALL 12 adapters (including indemnification, via its `accepted_anchors`-style feed) do the SAME thing architecturally: an admitted/discovered AI candidate's **offset span is fed back into the same window-building and deterministic re-parsing** that a regex-found anchor would go through (e.g. `payment_terms_policy_engine.py:734`: `anchor_spans = sorted([(m.start(), m.end()) for m in matches] + [(c.start_offset, c.end_offset) for c in admitted_semantic])`; identical pattern in insurance, confidentiality, data_security, governing_law, termination, warranties, sla, assignment, and liability's own `accepted_anchors` list). Supplementary qualifier fields (`ai_identified_condition`/`exception`/`definition_or_reference`) are ADDITIONALLY populated from the admission result, but the PRIMARY fact (net_days, cap amount, ownership_attributions, coverage.established, etc.) is **not** copied from the AI's own claim — it still requires the adapter's own narrow, per-value regex (e.g. `_NET_DAYS_RE = r"\bnet\s+(\d{1,3})\b"`, ip_ownership's `shall be owned by`-shaped attribution regex) to independently match **within the AI-widened window**.

**The real defect, precisely stated:** when the AI-discovered span's own phrasing does not ALSO satisfy that narrow per-value regex (which is common for colloquial/unusual phrasing — the exact case AI's contextual understanding is supposed to help with), the adapter falls through to "clause_found=True (or nothing at all), nothing established" — and depending on the adapter's own downstream branch structure, this silently resolves to **either** `NOT_APPLICABLE`/`CONFIRMED_ABSENT` (if nothing else in the document triggers ANY window at all) **or** a bare `ACCEPT`/"no policy gaps found" (if a window/clause_found=True state was reached but no specific requirement was structured) — never to a distinct, honest "a clause was found, and AI verified it, but its structured content could not be established" state. **This absent middle state (not the routing of AI's fields specifically) is the actual root cause.**

Indemnification's structuring code (its own party/trigger/monetary/condition parser) has a broader regex vocabulary tuned specifically to accept AI-discovered spans (Step 4A.9.2's explicit design goal), so it fails less often in practice — but it uses the exact same MECHANISM as the other 11, not a fundamentally different one. Root Cause 1 is therefore: **the shared architecture has no "PRESENT_BUT_UNRESOLVED"-equivalent state for "AI's proposition was verified ESTABLISHED and grounded, but the adapter's own value-extraction regex could not structure it"** — every adapter's absence-state vocabulary (`CONFIRMED_ABSENT`, `RECOGNITION_UNCERTAIN`, `DEPENDENCY_UNRESOLVED`) has a slot for "provider failed" and "nothing found at all," but not for "something was found and verified, but couldn't be fully parsed."

## Root Cause 3 (provider variance) — CONFIRMED via live repeatability testing in the prior mission

Directly observed, not re-derived: `ip_ownership-099` flipped `NOT_APPLICABLE` (3/5 real runs) vs `ACCEPT` (2/5 real runs) on the identical input. Mechanism, now precisely understood via the Root Cause 1 analysis above: in the `NOT_APPLICABLE` runs, the OpenAI call returned zero candidates or a non-ESTABLISHED verification that run (a legitimate recall miss); in the `ACCEPT` runs, the AI candidate WAS admitted (ESTABLISHED, grounded), but fell into the "clause found, nothing structured" branch and reached `ACCEPT` via "no policy gaps found" — i.e., **Root Cause 3 is a direct, mechanical consequence of Root Cause 1's missing middle state, not an independent defect requiring its own separate fix.** Once an admitted-but-unstructured candidate routes to a distinct, safe `PRESENT_BUT_UNRESOLVED` → `REQUIRES_REVIEW` state instead of `ACCEPT`, the specific forbidden `ACCEPT ↔ NOT_APPLICABLE` transition is eliminated by construction. The residual variance (`NOT_APPLICABLE` when AI happens not to notice a genuinely-present, unusually-phrased clause at all, vs. `REQUIRES_REVIEW` when it does) is an inherent, acknowledged recall-variance limit of probabilistic discovery, not a fabricated-clean-answer violation — and matches the mission's own stated tolerance (Section 15: "If provider variance exposes unresolved material uncertainty and all such runs safely route to review, that is acceptable").

## Per-adapter map (fields 1–12)

For all 11 shared-framework adapters the answers to fields 1–9 are structurally identical (only the specific regexes/Facts-field names differ); indemnification differs as noted. Rather than repeat 11 near-identical tables, the shared answer is given once, with the per-adapter specifics that actually vary (field name, primary-fact regex, decision states) tabulated below it.

### Shared answer (liability, confidentiality, payment_terms, ip_ownership, insurance, data_security, governing_law, termination, warranties, sla, assignment)

1. **Deterministic discovery path**: adapter-specific `_ANCHOR_RE`/`_DIRECT_MENTION_RE`-family regex(es) over the full document text.
2. **AI discovery invocation point**: adapter's own `_run_semantic_discovery()`, called ONLY `if not <anchors/matches>:` (Root Cause 2).
3. **CandidateMaterialFact construction**: `fact_admission.discover_candidate_spans(text, "<adapter>", <FOCUS>)` — verbatim-grounded via exact substring search.
4. **Deterministic verification**: `fact_admission.verify_candidate_proposition()` (adversarial verifier) inside `verify_and_ground()`.
5. **Deterministic grounding**: `fact_admission.ground_evidence_quote()` + `ground_qualifiers()` + `resolve_definition()`/`resolve_cross_reference_target()`/`ground_competing_readings()`, all inside `verify_and_ground()`.
6. **Admission**: `fact_admission.evaluate_admission()` — `ADMITTED` only on ESTABLISHED + grounding pass + no unresolved dependency/conflict + all qualifiers grounded.
7. **Canonical fact representation**: none distinct from the adapter's own Facts dataclass — admitted candidates' offsets are merged into `anchor_spans`/windows (Root Cause 1 mechanism above), and `ai_identified_condition`/`exception`/`definition_or_reference` are copied onto the Facts object.
8. **Adapter consumption**: the adapter's own per-value regex re-parses the (possibly AI-widened) window; if it matches, the primary fact is set; if not, nothing is set for that admitted candidate (Root Cause 1 defect).
9. **Policy decision**: `evaluate_<adapter>_policy()` in `policy_engine_core.py`'s shared 8-state vocabulary.
10. **Absence handling**: `absence_state` field — `CONFIRMED_ABSENT` (both channels found nothing) vs `RECOGNITION_UNCERTAIN` (provider errored) vs (payment_terms/liability only) `DEPENDENCY_UNRESOLVED` (candidate found but its cross-reference/definition dependency unresolved). **No adapter has a state for "AI admitted ESTABLISHED, deterministic couldn't structure it"** (the gap this mission fixes).
11. **Ambiguity handling**: `ground_competing_readings()` returns 0–2 `CompetingReading` objects on the candidate; `evaluate_admission()` blocks admission if 2+ are independently grounded — but this only applies to AI-sourced candidates. A CONTRADICTION expressed entirely in deterministic, non-AI-invoking text (both anchors match, i.e. Root Cause 2's gate never lets AI see it) has no analogous protection today (confirmed empirically: 10 `ARBITRARILY_SELECTED_COMPETING_READING` violations in the Candidate 3 burned corpus, concentrated in cases where AI was never invoked at all).
12. **Interaction participation**: via `PolicyDecision.state` only — `interaction_engine_core._gate_participants()` treats `NOT_APPLICABLE`/`REQUIRES_REVIEW`/`EVALUATION_ERROR` as unsafe-to-reason-over and gates the whole interaction to `INSUFFICIENT_FACTS` (confirmed working correctly in the Candidate 3 report's Section 11 tests — not touched by this remediation).

### Per-adapter specifics

| Adapter | Primary-fact field | Primary-fact regex (narrow) | Absence states available |
|---|---|---|---|
| limitation_of_liability | `provisions` / `controlling_provision` | `_extract_provision`'s cap/multiplier parsing | CONFIRMED_ABSENT, RECOGNITION_UNCERTAIN, DEPENDENCY_UNRESOLVED |
| confidentiality | `obligations` (directional) | `_NAMED_OBLIGATION_RE` / `_MUTUAL_OBLIGATION_RE` | CONFIRMED_ABSENT, RECOGNITION_UNCERTAIN |
| payment_terms | `net_days` | `_NET_DAYS_RE` (`net\s+(\d{1,3})`), `_WITHIN_DAYS_PAYMENT_RE` (digits only, no spelled-out numbers) | CONFIRMED_ABSENT, RECOGNITION_UNCERTAIN, DEPENDENCY_UNRESOLVED |
| ip_ownership | `ownership_attributions` | attribution regex requiring an explicit `shall be owned by`/`assigns...to`/`is owned by`-shaped verb | CONFIRMED_ABSENT, RECOGNITION_UNCERTAIN |
| insurance | `coverages[ct].established` | per-coverage-type `_COVERAGE_RES` (named types only: CGL, professional liability, cyber, workers' comp, etc. — no generic "risk-transfer" catch-all) | CONFIRMED_ABSENT, RECOGNITION_UNCERTAIN |
| data_security | `breach_notification_hours` / `role_attributions` / etc. | `_BREACH_HOURS_RE`, `_BREACH_CALENDAR_DAYS_RE`, `_BREACH_BUSINESS_DAYS_RE` (Candidate 2 already broadened this to accept spelled-out numbers) | CONFIRMED_ABSENT, RECOGNITION_UNCERTAIN |
| governing_law | `jurisdiction` | direct `governed by the laws of <state>`-shaped regex | CONFIRMED_ABSENT, RECOGNITION_UNCERTAIN |
| termination | `rights` | right-grant regex per termination type | CONFIRMED_ABSENT, RECOGNITION_UNCERTAIN |
| warranties | `categories[cat].established` | per-category warranty regex + `found_anything` gate | CONFIRMED_ABSENT, RECOGNITION_UNCERTAIN |
| sla | `uptime_percent` / `service_credit_present` | `_UPTIME_WITH_PERCENT_RE` (requires a `%` figure) + `found_anything` gate | CONFIRMED_ABSENT, RECOGNITION_UNCERTAIN |
| assignment | `restrictions` / `unrestricted_assignment` | restriction-grant regex | CONFIRMED_ABSENT, RECOGNITION_UNCERTAIN |

### indemnification (structurally different, per Section 11 of the mission)

1. **Deterministic discovery**: `_ANCHOR_RE` plus several structured synonym patterns plus a broad risk-transfer SIGNAL regex (`_RISK_TRANSFER_SIGNAL_RE`) — deliberately the widest deterministic vocabulary of any adapter.
2. **AI discovery invocation**: unconditional (`HYBRID_DISCOVERY_ENABLED=True`), via `_discover_candidate_spans()` → `semantic_discovery_real.discover_candidate_spans_real` (when `SEMANTIC_PROVIDER="REAL"`) — Root Cause 2 already fixed here, pre-existing.
3–6. Same `fact_admission.py` primitives as the shared framework, but ONLY for the SECOND, additive reconciliation channel (`INDEMNIFICATION_RECONCILIATION_ENABLED`); the PRIMARY discovery path uses `semantic_discovery.DiscoveryCandidate` (a narrower schema, no verify/ground/admit pipeline of its own — offset-grounding only) and hands the grounded span directly to indemnification's own deterministic structuring parser.
7. **Canonical representation**: `IndemnityObligation`, populated identically regardless of whether the span came from regex or AI.
8. **Adapter consumption**: the SAME deterministic structuring parser runs on both regex- and AI-sourced spans — this is why indemnification is closer to (but not identical to) the target architecture this mission builds for the other 11.
9–12: same as shared framework via `evaluate_indemnification_policy()`.

**Decision for this mission (Section 11 of the mission brief):** indemnification is NOT replaced. Its existing hybrid mechanism is preserved as-is. The remediation below generalizes the *outcome* indemnification already achieves (an admitted-but-unstructured finding is never silently discarded) to the other 11 adapters via an adapter-appropriate mechanism, not via forcing indemnification's own code path onto them.
