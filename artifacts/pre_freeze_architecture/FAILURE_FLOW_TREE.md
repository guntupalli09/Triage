PRE-FREEZE INSPECTION — INSPECTION ONLY, NO CODE CHANGED

# Failure Flow Tree — every uncertainty path and its terminal state

Desired invariant: UNCERTAINTY → REVIEW/ESCALATE/ERROR → NEVER CLEAN.

| Branch | Code path (file:line) | Terminal state | Verdict |
|---|---|---|---|
| Extraction empty (no anchor, no AI candidate, no error) | `extract_*_facts` returns `None` when nothing found anywhere, e.g. `data_security_policy_engine.py:589-590` | `NOT_APPLICABLE` | Safe — genuinely nothing found |
| Extraction near-empty (anchor found, nothing structured, no AI signal) | e.g. `sla_policy_engine.py:758` `if not found_anything: ... return None` | `NOT_APPLICABLE` | Safe within current corroboration design |
| AI unavailable (exception in discovery) | `_run_semantic_discovery`'s `except Exception` catch, e.g. `data_security_policy_engine.py:552-555` → `semantic_error` set | `RECOGNITION_UNCERTAIN` → `REQUIRES_REVIEW` (or deterministic-only decision if an anchor exists) | Safe |
| AI timeout | Same exception path (30s hardcoded timeout, `fact_admission.py:333`, zero retries) | Same as above | Safe (fail-closed, though zero-retry means a single transient blip forces review with no self-heal) |
| AI malformed output / empty output | `_call_model` shape/JSON checks (`fact_admission.py:400-413`) → `ProviderUnavailable`, or empty candidate list | `NOT_APPLICABLE` (no anchor) or deterministic-only decision | Safe — never asserts a false positive |
| **AI uncertain verification (NOT_ESTABLISHED/AMBIGUOUS/INSUFFICIENT_CONTEXT/CONFLICTING)** | `first_unresolved_dependency_note`'s catch-all (`fact_admission.py`, gated on `_PARTY_OBLIGATION_ANCHOR_RE`), wired through 7 adapters' "nothing else established" gates + 4 adapters' unconditional force | `PRESENT_BUT_UNRESOLVED`/`REQUIRES_REVIEW` | **Safe for the 11 adapters using `fact_admission.py`; see indemnification exception below** |
| **AI verification error (VERIFICATION_ERROR — a provider failure specifically on the per-candidate verify call, distinct from discovery failure)** | `_UNCERTAIN_VERIFICATION_STATES` in `first_unresolved_dependency_note` **excludes `VERIFICATION_ERROR`** (confirmed live in this audit) | If deterministic regex also finds nothing: **`NOT_APPLICABLE`** | 🚨 **FALSE-CONFIDENCE PATH — FREEZE BLOCKER.** A genuine AI-proposed, offset-grounded candidate whose verification call failed (not whose verification said "uncertain" — an actual provider error mid-pipeline) is invisible to the escalation mechanism and can collapse to a clean "no clause" result. |
| Evidence not verbatim (grounding fails) | `ground_evidence_quote` (`fact_admission.py:634-645`) | Falls through to whichever absence/uncertain state applies; never silently accepted | Safe |
| Evidence location invalid | Same grounding gate | Same | Safe |
| Condition ungrounded / exception ungrounded | `ground_qualifiers` (`fact_admission.py:679-690`) blocks admission of the qualifier | Qualifier not attached to an admitted candidate | Safe |
| Definition unresolved | `first_unresolved_dependency_note`'s definition branch (`fact_admission.py:1079-1084`) | `DEPENDENCY_UNRESOLVED` / `REQUIRES_REVIEW` | Safe, subject to the same "nothing else established" suppression noted in AUTHORITY_FLOW_TREE.md #2 for a *separate, unrelated* candidate |
| Cross-reference unresolved | `first_unresolved_dependency_note`'s cross-reference branch (`fact_admission.py:1085-1090`) | `DEPENDENCY_UNRESOLVED` / `REQUIRES_REVIEW` | Same caveat as above |
| Referenced attachment missing | Same cross-reference path, `CrossReferenceResolution.status == "MISSING_ATTACHMENT"` | `DEPENDENCY_UNRESOLVED` / `REQUIRES_REVIEW` | Safe, same caveat |
| Competing readings (≥2 grounded) | `evaluate_admission` blocks admission outright (`fact_admission.py:913-923`); `first_unresolved_dependency_note`'s branch (1091-1104) surfaces it for a NOT_ADMITTED candidate | `REQUIRES_REVIEW` | Safe at the admission gate; note-surfacing subject to the same suppression caveat |
| Descriptive/non-operative language | `_PARTY_OBLIGATION_ANCHOR_RE` correctly does not match (live-tested) → verifier's confident rejection stands | `NOT_APPLICABLE`/`CONFIRMED_ABSENT` | Correct by design — this is the case the fix was built to leave alone |
| Explicit negation | `_DIRECT_OBLIGATION_NEGATION_RE` (`policy_engine_core.py:1813-1821`) — live-tested, correctly fires on "shall not be required to" | Adapter-specific negation flag | Safe |
| **Document-wide contradiction** | `document_wide_conflict_detected`/`unreconciled_ambiguity_marker_present` (`policy_engine_core.py:1872-1888`), consumed via `facts.document_wide_conflict`, NOT routed through the note-suppression mechanism | `REQUIRES_REVIEW` unconditionally | Safe — not subject to the suppression caveat since it's adapter-local, not AI-note-based |
| AI/deterministic disagreement | No distinct branch — AI-sourced qualifiers are additive to, never override, deterministic values (e.g. `liability_policy_engine.py:1812-1836`'s composition, only fires when deterministic condition is `UNCONDITIONAL`) | Composed into REQUIRES_REVIEW-forcing fields | Safe |
| Deterministic extraction miss (AI found something regex didn't) | `admitted_semantic` seeds `accepted_anchors` when regex found nothing at all (e.g. `liability_policy_engine.py:1736-1737`); when regex found a *different* anchor, see AUTHORITY_FLOW_TREE.md #4 | `PRESENT_BUT_UNRESOLVED`/`MUST_REDLINE` (no anchor case) or **silently dropped** (anchor-exists-elsewhere case, liability only, acknowledged in-code as a residual risk) | Partial — safe for the primary "clause exists at all" question; a documented gap for a second, separate fact in liability specifically |
| Adapter evaluation exception | `policy_enforcement.py:453-468`, per-clause-type try/except isolates to `EVALUATION_ERROR` | `EVALUATION_ERROR`, high severity, routed to manual review | Safe |
| Interaction participant uncertainty | `interaction_engine_core._gate_participants` (`interaction_engine_core.py:222-241`) | `INSUFFICIENT_FACTS`, never a clean verdict | Safe |
| **Indemnification's reconciliation-channel verification failure** | `indemnification_policy_engine.py:167-170`, unconditional/unguarded consumption of `first_unresolved_dependency_note`'s output, no equivalent to liability's `_any_provision_established` gate | Can flip between a clean, independently-and-correctly-derived monetary/scope outcome and `REQUIRES_REVIEW` across identical real-provider runs, for an obligation whose only unresolved dimension is `condition` | 🚨 **ARCHITECTURAL BLOCKER (repeatability/determinism, not raw false-confidence — both terminal states are individually legitimate, but the SAME input should not non-deterministically choose between them)**. Never included in the repeatability corpus (`data_security-139`/`ip_ownership-080`/`ip_ownership-086`/`limitation_of_liability-006` are the only cited cases) so this gap was never empirically caught. |

## Summary

Of 22 traced branches, **20 correctly fail closed** (uncertainty → review/escalate/error,
never clean). **Two branches are confirmed unsafe:**

1. 🚨 **FALSE-CONFIDENCE PATH — FREEZE BLOCKER**: `VERIFICATION_ERROR` on a per-candidate
   verify call is invisible to `first_unresolved_dependency_note`, and can collapse to
   `NOT_APPLICABLE` when deterministic regex also misses. This is a genuine
   uncertainty→clean path, not merely a determinism/flakiness concern.
2. 🚨 **ARCHITECTURAL BLOCKER (determinism)**: indemnification's reconciliation `else`
   branch has no "nothing else established" gate, exposing it to the exact
   `limitation_of_liability-006` failure shape, uncaught by the existing repeatability
   corpus.

Neither of these produces a raw-AI-sourced ACCEPT (the `evaluate_admission` gate itself
is intact in both cases) — both are escalation/absence-classification leaks at the
adapter-composition layer, one full step removed from the admission boundary itself.
