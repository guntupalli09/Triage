PRE-FREEZE INSPECTION — INSPECTION ONLY, NO CODE CHANGED

# Adapter Architecture Matrix

PASS = executable, adapter-specific proof verified in this audit. PARTIAL = proof exists but
with a documented, narrower gap. N/A = dimension genuinely doesn't apply. UNKNOWN = not
verified to full depth in this pass (not assumed safe).

| Adapter | AI discovery | Primary fact consumption | Condition | Exception | Definition | Cross-ref | Competing readings | Operative context | Unresolved propagation | Deterministic grounding | Fail closed | Decision sensitivity | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| limitation_of_liability | PASS | PASS | PASS | PASS | PASS | UNKNOWN | PASS (inherited) | PASS (shared primitive) | PARTIAL (residual non-matching-offset drop, documented in-code) | PASS | PASS | PASS | liability_policy_engine.py:1734-2296 |
| indemnification | FAIL (default channel is simulated regex, not AI — no env override) | N/A (different scenario — not `fact_admission`-ADMITTED by default) | PARTIAL (narrower gate than liability) | PARTIAL | PARTIAL | PARTIAL | PASS (inherited, reconciliation channel only) | PASS (shared primitive, reconciliation channel only) | FAIL (unguarded else branch, uncaught by repeatability corpus) | PASS | PASS | PASS | indemnification_policy_engine.py:80,89,115-170,3461-3520 |
| confidentiality | PASS | UNKNOWN (not independently traced to full depth) | PASS | PASS | PASS (unconditional) | PASS (unconditional) | PASS (inherited) | UNKNOWN | PASS (unconditional, verified end-to-end) | PASS | PASS | PASS | confidentiality_policy_engine.py:343-347,447,570,617 |
| payment_terms | PASS | UNKNOWN | PASS | PASS | PASS | PASS | PASS (inherited) | UNKNOWN | PASS (`_any_established`-gated, structurally consistent) | PASS | PASS | PASS | payment_terms_policy_engine.py:730-733,1052-1071 |
| ip_ownership | PASS | UNKNOWN | PASS | PASS | PASS | PASS | PASS (inherited) | UNKNOWN | PASS (`_any_other_established`-gated) | PASS | PASS | PASS | ip_ownership_policy_engine.py:617-620,750-763 |
| insurance | PASS | PASS (verified end-to-end) | PASS | PASS | PASS | PASS | PASS (inherited) | UNKNOWN | PASS (`deterministic_value_found`-gated, verified end-to-end) | PASS | PASS | PASS | insurance_policy_engine.py:395-405,630-634,790-794 |
| data_security | PASS | UNKNOWN | PASS | PASS | PASS | PASS | PASS (inherited) | UNKNOWN | PASS (`_any_established`-gated, structurally consistent) | PASS | PASS | PASS | data_security_policy_engine.py:585-588,755-769 |
| governing_law | PASS | UNKNOWN | PASS | PASS | PASS (unconditional) | PASS (unconditional) | PASS (inherited) | UNKNOWN | PASS (unconditional, verified end-to-end) | PASS | PASS | PASS | governing_law_policy_engine.py:182-185,206,313 |
| termination | PASS | UNKNOWN | PASS | PASS | PASS (unconditional) | PASS (unconditional) | PASS (inherited) | UNKNOWN | PASS (unconditional, verified end-to-end) | PASS | PASS | PASS | termination_policy_engine.py:458-461,559,720 |
| warranties | PASS | UNKNOWN | PASS | PASS | PASS | PASS | PASS (inherited) | UNKNOWN | PASS (`found_anything`-gated, structurally consistent) | PASS | PASS | PASS | warranties_policy_engine.py:464-467,627-646 |
| sla | PASS | UNKNOWN | PASS | PASS | PASS | PASS | PASS (inherited) | UNKNOWN | PASS (`found_anything`-gated, structurally consistent) | PASS | PASS | PASS | sla_policy_engine.py:466-469,758-777 |
| assignment | PASS | UNKNOWN | PASS | PASS | PASS (unconditional) | PASS (unconditional) | PASS (inherited) | UNKNOWN | PASS (unconditional, verified end-to-end) | PASS | PASS | PASS | assignment_policy_engine.py:252-255,319,454 |

## Notes on this matrix's honesty

- "AI discovery" PASS for 11 adapters means: `_run_semantic_discovery` is called unconditionally
  (not gated behind "regex found nothing") AND is env-controllable via
  `<ADAPTER>_SEMANTIC_DISCOVERY_ENABLED`/`FACT_ADMISSION_MODE`. Indemnification's primary channel
  fails both of the underlying premises for a different reason (it's not AI at all by default).
- "Unresolved propagation" PASS for all 11 mirror adapters is a claim about **whether the note
  reaches the decision when it fires** — it is NOT a claim that the note fires correctly for
  every uncertainty class. See FAILURE_FLOW_TREE.md: the shared `first_unresolved_dependency_note`
  function itself has a confirmed gap (VERIFICATION_ERROR not covered), which every PASS in this
  column inherits regardless of the adapter's own wiring quality.
- "Operative context" is marked UNKNOWN for 10 of 12 adapters because the shared primitive
  (`policy_engine_core.is_operative_context`) was live-tested and found to have real gaps
  (future/hypothetical framing, unquoted illustrative examples, historical-agreement references,
  explicit "illustrative only" labels — all classified `OPERATIVE_CONFIRMED` with no hedge) —
  whether a given adapter's own anchor regex independently protects against each of these four
  shapes was not individually verified per adapter, so per-adapter PASS is not asserted.
- "Decision sensitivity" (does an AI signal ever override rather than merely augment a
  deterministic one) is PASS everywhere checked — no adapter was found to let an AI value
  override an established deterministic value; AI composition is uniformly additive.
