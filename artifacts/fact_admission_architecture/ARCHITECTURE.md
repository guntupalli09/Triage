# ARCHITECTURE — Fact Admission / Semantic Verification

Status: describes what is actually implemented as of this commit, not an
aspirational design. See PRE_IMPLEMENTATION_MAP.md for the investigation
this was built on, and RESIDUAL_RISK_REGISTER.md for what remains.

## Pipeline

```
CONTRACT
  -> INGESTION QUALITY GATE        upload_security.assess_pdf_text_density
                                    (near-empty PDF extraction rejected)
  -> CLAUSE DISCOVERY
       deterministic (regex)       per-adapter _ANCHOR_RE, unchanged
       semantic (AI, additive)     fact_admission.discover_candidate_spans
                                    -- runs ONLY when deterministic finds
                                    nothing, per adapter opt-in flag
  -> SEMANTIC VERIFICATION         fact_admission.verify_candidate_proposition
                                    -- adversarial: tries to DISPROVE the
                                    candidate proposition, not confirm it
  -> DETERMINISTIC GROUNDING       fact_admission.ground_evidence_quote
                                    -- exact-substring check, independent
                                    of AI, on the verifier's own citation
  -> ADMISSION GATE                fact_admission.evaluate_admission
                                    -- ADMITTED only if ESTABLISHED +
                                    grounding PASS + no unresolved
                                    dependency/conflict
  -> existing deterministic per-adapter extract_*_facts/evaluate_*_policy
       (an admitted semantic candidate is treated as an ordinary anchor —
       it still has to survive the SAME deterministic structuring a
       regex-found anchor does; it never bypasses it)
  -> policy_engine_core.PolicyDecision            (unchanged)
  -> interaction_engine_core.evaluate()           (unchanged, already
       fails closed on any unsafe participant state)
  -> document_aggregation.aggregate_document_state()  (unchanged; now
       rendered on all three user-facing surfaces: dashboard, history,
       and the single-contract review page)
  -> USER RESULT
```

## What is new in this change

- `fact_admission.py` — the shared, adapter-agnostic framework (states,
  `CandidateMaterialFact`, discovery, adversarial verification,
  grounding, the one admission gate). See AUTHORITY_BOUNDARY.md.
- `liability_policy_engine.py` — the reference adapter integration,
  gated behind `LIABILITY_SEMANTIC_DISCOVERY_ENABLED` (default `False`).
- `main.py` / `templates/review.html` — the single-contract review page
  now surfaces the same authoritative "Needs Attention" badge the
  dashboard/history pages already had.
- `upload_security.py` — `assess_pdf_text_density`, the near-empty
  extraction gate.

## What is unchanged (deliberately)

- `policy_engine_core.py`, `interaction_engine_core.py`,
  `document_aggregation.py` — already implement the authority boundary,
  fail-closed interaction gating, and false-clean invariant this mission
  asks for. No changes were needed there; extending them was not in scope
  because they were already correct (see PRE_IMPLEMENTATION_MAP.md §4/§7/§8).
- `indemnification_policy_engine.py`'s own semantic-discovery pathway
  (`semantic_discovery.py` / `semantic_discovery_real.py`) — left as-is.
  It is a separately frozen, already-validated (Step 4B) implementation
  of the same pattern this mission generalizes; migrating it onto
  `fact_admission.py` is a follow-on, not required for correctness, and
  risks disturbing a frozen validation result for no safety benefit.
- The 10 remaining adapters (confidentiality, payment_terms, ip_ownership,
  insurance, data_security, governing_law, termination, warranties, sla,
  assignment) — not yet integrated. See ADAPTER_MATRIX.md.

## Rollout discipline

Every new adapter integration must, like liability's:
1. Add an `absence_state` field (`CONFIRMED_ABSENT` default /
   `RECOGNITION_UNCERTAIN` on provider failure), mirroring
   `IndemnificationFacts` exactly.
2. Gate real-provider calls behind a per-adapter, default-`False` module
   constant, so no environment's behavior changes merely because
   `ANTHROPIC_API_KEY` happens to be set or unset.
3. Treat a semantically-admitted candidate as an ordinary anchor into the
   adapter's own existing deterministic structuring — never as a
   structured fact in its own right.
4. Route `RECOGNITION_UNCERTAIN` to `REQUIRES_REVIEW`, never
   `NOT_APPLICABLE`, in the adapter's `evaluate_*_policy` absence branch.
5. Ship with adapter-specific tests covering: disabled-by-default no-op,
   provider-outage fail-closed, hallucinated-quote rejection, a verified
   end-to-end admission, and the descriptive/background-language
   regression (Step 15's general failure class).
