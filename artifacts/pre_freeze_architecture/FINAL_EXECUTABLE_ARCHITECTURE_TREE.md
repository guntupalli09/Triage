PRE-FREEZE INSPECTION — INSPECTION ONLY, NO CODE CHANGED
Branch: `claude/final-trust-architecture-cutover` — HEAD `7bf099f`

# Final Executable Architecture Tree (as traced from actual call sites)

This is the REAL wiring, not the idealized pipeline in the mission brief. The single
most important divergence: **the pipeline forks on `POLICY_ENFORCEMENT_MODE`, and the
idealized 12-adapter/interaction-engine/aggregation chain only executes in `cutover`
mode.** Default (`shadow`) mode runs a completely different, narrower path.

```
UPLOAD (main.py:1406 upload_contract)
  │  DETERMINISTIC / NON-AUTHORITATIVE
  │  IN: raw file bytes  OUT: contract_text  FAIL: caught, user-facing upload error
  ▼
EXTRACTION (extract_text_from_file, called main.py:1447)
  ▼
LEGACY RULE ENGINE (rule_engine.analyze, main.py:317-319)
  │  computes Contract.overall_risk BEFORE policy enforcement ever runs
  ▼
POLICY ENFORCEMENT DISPATCH — policy_enforcement.apply_policies_for_review
  (policy_enforcement.py:751-809)  DETERMINISTIC dispatcher / AUTHORITATIVE
  │
  │  mode = get_enforcement_mode() = os.getenv("POLICY_ENFORCEMENT_MODE","shadow")
  │  (policy_enforcement.py:52,150-153) — freshly read every call, defaults to "shadow"
  │
  ├── mode ∈ {shadow, legacy} (THE DEFAULT) ─────────────────────────────────┐
  │     policy_enforcement.py:796-809                                        │
  │     apply_liability_policy() → liability_policy_engine only              │
  │     interaction_decisions = None (hard-set, line 809)                    │
  │     ALL OTHER 11 ADAPTERS NEVER RUN. INTERACTION ENGINE NEVER RUNS.      │
  │                                                                           │
  └── mode == "cutover" (must be explicitly set) ────────────────────────────┤
        policy_enforcement.py:776-794                                        │
        apply_active_policies → evaluate_active_policies                     │
        (policy_enforcement.py:418-469)                                      │
          for each of pa.CLAUSE_TYPES (12, playbook_authoring.py:73-87):     │
            skipped entirely if no ACTIVE PolicyPosition for that clause     │
            type on this playbook (policy_enforcement.py:449-451)            │
          │                                                                  │
          ├── DETERMINISTIC ANCHOR DISCOVERY (per adapter regex)             │
          │     [adapter_policy_engine.py: _ANCHOR_RE / _discover_anchors]   │
          │     DETERMINISTIC / NON-AUTHORITATIVE (feeds structuring only)   │
          │     runs unconditionally, independent of AI flags                │
          │                                                                  │
          ├── AI CONTEXTUAL DISCOVERY — fact_admission.discover_candidate_spans│
          │     (fact_admission.py:442-473)  AI / NON-AUTHORITATIVE          │
          │     gated per-adapter by <ADAPTER>_SEMANTIC_DISCOVERY_ENABLED    │
          │     (default False for 11/12 adapters; see CONFIGURATION_        │
          │     ACTIVATION_MATRIX.md — indemnification is a hardcoded        │
          │     exception, see below)                                       │
          │     IN: text+focus  OUT: List[CandidateMaterialFact]             │
          │        (evidence_span/start_offset/end_offset only, offsets by   │
          │        exact substring match, never trusted from the model)      │
          │     FAIL: any provider/network/JSON error → ProviderUnavailable  │
          │        → adapter's semantic_error string (never "found nothing") │
          │     NEXT: verify_and_ground, per candidate                       │
          │                                                                  │
          ├── SEMANTIC VERIFICATION + GROUNDING —                            │
          │     fact_admission.verify_and_ground (fact_admission.py:953-977) │
          │     composes: verify_candidate_proposition (AI, 557),            │
          │       ground_evidence_quote (DETERMINISTIC, 634),                │
          │       ground_qualifiers (DETERMINISTIC, 679),                    │
          │       resolve_definition / resolve_cross_reference_target        │
          │         (DETERMINISTIC, regex-only, 696/751),                    │
          │       ground_competing_readings (DETERMINISTIC, 808),            │
          │       evaluate_admission (DETERMINISTIC / AUTHORITATIVE GATE,829)│
          │     OUT: candidate mutated, admission_status ∈ {ADMITTED,        │
          │       NOT_ADMITTED}                                              │
          │     FAIL: provider error → VERIFICATION_ERROR → always           │
          │       NOT_ADMITTED (fact_admission.py:110-113, 861-864)          │
          │                                                                  │
          ├── DETERMINISTIC STRUCTURING (per-adapter _extract_provision/     │
          │     equivalent) — merges admitted AI candidates with regex       │
          │     anchors; see TWELVE_ADAPTER_TREE.md and AUTHORITY_FLOW_TREE  │
          │     for the exact, adapter-specific merge/drop rules — this is   │
          │     where the ARCHITECTURAL BLOCKERS documented in this audit    │
          │     live, not in discovery/verification/admission themselves.    │
          │                                                                  │
          ├── ADAPTER EVALUATION — evaluate_<clause>_policy                  │
          │     DETERMINISTIC / AUTHORITATIVE (the only place a              │
          │     PolicyDecision.state is ever assigned)                       │
          │     OUT: PolicyDecision (state ∈ ACCEPT/ACCEPT_WITH_NOTE/        │
          │       NEGOTIATE/MUST_REDLINE/PROHIBITED/ESCALATE/REQUIRES_REVIEW/│
          │       NOT_APPLICABLE — not all adapters reach all states, see    │
          │       TWELVE_ADAPTER_TREE.md)                                    │
          │     FAIL: exception isolated per-clause-type to EVALUATION_ERROR │
          │       (policy_enforcement.py:453-468) — never a fabricated       │
          │       decision, never blocks other clause types                  │
          │                                                                  │
          ▼                                                                  │
        INTERACTION ENGINE — interaction_engine_core.evaluate                │
          (interaction_engine_core.py:244-332)                               │
          DETERMINISTIC / AUTHORITATIVE for interaction findings             │
          consumes ONLY already-computed PolicyDecision objects — never      │
          raw text, never a new LLM call (module docstring, lines 8-13)      │
          gate: refuses to run a rule predicate if any participating         │
          clause type's decision state ∈ {NOT_APPLICABLE, REQUIRES_REVIEW,   │
          EVALUATION_ERROR} (interaction_engine_core.py:92,222-241) →        │
          emits INSUFFICIENT_FACTS instead, never a clean verdict            │
          Only 6/12 adapters ever participate in a launch-catalog rule       │
          (limitation_of_liability, indemnification, insurance,              │
          termination, payment_terms, sla — interaction_rules.py:275-323)    │
          called from policy_enforcement.py:792-793, ONLY in cutover mode    │
  ▼
PERSISTENCE — Contract row (main.py:1520-1562)
  policy_decisions_json / interaction_decisions_json: EncryptedJSON columns
  (models.py) — see PART 4/HISTORICAL REPRODUCIBILITY notes in the verdict
  for exactly what does and does not survive per decision
  ▼
UNIFIED DOCUMENT AGGREGATION — document_aggregation.aggregate_document_state
  (document_aggregation.py:149-198), a READ-TIME pure function, re-run on
  every page render (not gated by either env var)
  DETERMINISTIC / AUTHORITATIVE (never recomputes underlying decisions)
  precedence: interaction ESCALATE → HAS_CRITICAL_INTERACTION;
  policy PROHIBITED/MUST_REDLINE/ESCALATE/NEGOTIATE → HAS_POLICY_VIOLATION;
  any REQUIRES_REVIEW/EVALUATION_ERROR/INSUFFICIENT_FACTS/malformed →
  REQUIRES_REVIEW; cutover-with-no-decisions → CONFIGURATION_UNRESOLVED;
  legacy overall_risk=="high" with nothing else → CLEAN_LEGACY_ATTENTION;
  else CLEAN
  ▼
PRESENTATION — surfaced INCONSISTENTLY (see 🚨 UI AUTHORITY BLOCKER):
  ├── DASHBOARD (main.py:1291-1324)            — reads document_state ✅
  ├── HISTORY (main.py, /history)               — reads document_state ✅
  ├── SINGLE-CONTRACT REVIEW (in-progress page) — reads document_state ✅
  ├── FULL REPORT / AUDIT TRAIL (results.html)  — overall_risk ONLY ❌
  ├── PDF EXPORT (_build_pdf_bytes)              — overall_risk ONLY ❌
  ├── NEGOTIATION PACKAGE (redline/memo/zip)     — no aggregated state ❌
  └── EXTERNAL SHARED REPORT LINK                — overall_risk ONLY ❌
```

## The one hardcoded, non-conforming adapter: indemnification

`indemnification_policy_engine.py`'s primary discovery channel (`HYBRID_DISCOVERY_ENABLED
= True`, line 80, unconditional / no env override) dispatches to `semantic_discovery.py`'s
`SEMANTIC_PROVIDER = "SIMULATED"` (line 89, a bare module constant with **no**
`os.environ` read anywhere in the file) — an ordinary hand-written regex proposer, **not
a language model**, regardless of `FACT_ADMISSION_MODE`. Its separate, genuinely
`fact_admission`-backed real-AI channel (`INDEMNIFICATION_RECONCILIATION_ENABLED`, off
by default, env-gated like the other 11 adapters) only *reconciles* obligations the
deterministic engine already found — it never discovers new ones. See
`TWELVE_ADAPTER_TREE.md` §2 and the verdict's "known configuration blockers" section.
