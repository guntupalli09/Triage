# ARCHITECTURE — Final Trust Architecture

This document describes what is actually implemented on this branch, not
an aspirational target. See PRE_IMPLEMENTATION_MAP.md for the Phase 0
investigation and RESIDUAL_RISK_REGISTER.md for what remains open.

## Pipeline as implemented today

```
CONTRACT
  -> upload_security.assess_pdf_text_density()   [near-empty PDF rejected]
  -> rules_engine.RuleEngine.analyze()            [LEGACY, unchanged]
  -> policy_enforcement.apply_policies_for_review()
       mode = get_enforcement_mode()  (env POLICY_ENFORCEMENT_MODE, default "shadow")
       ── mode == "cutover" ──────────────────────────────────────────────
       │  for each of 12 clause_types with an ACTIVE PolicyPosition:
       │    extract_<clause>_facts(text)
       │      deterministic anchor/regex discovery (unchanged, per adapter)
       │      + fact_admission.discover_candidate_spans() (additive, only
       │        when the deterministic anchor finds nothing) [11/12 adapters;
       │        indemnification uses its own separate, pre-existing mechanism]
       │      -> fact_admission.verify_and_ground() (adversarial verify +
       │         exact-substring grounding) -> ADMITTED candidates only ever
       │         seed the SAME pre-existing deterministic structuring function
       │         a regex anchor would -- never bypass it
       │    evaluate_<clause>_policy(facts, position) -> PolicyDecision
       │  -> interaction_enforcement.apply_interaction_rules(outcomes, findings)
       │     -> interaction_engine_core.evaluate() (fails closed on any
       │        unsafe participant state, unchanged)
       └────────────────────────────────────────────────────────────────
       ── mode == "legacy" or "shadow" (the default) ─────────────────────
       │  apply_liability_policy() ONLY -- the pre-modern, liability-only
       │  legacy path is the user-visible result. In "shadow" mode the
       │  modern engine above also runs, diagnostically, via
       │  run_shadow_comparison() -- explicitly never affects what the
       │  user sees.
       └────────────────────────────────────────────────────────────────
  -> document_aggregation.aggregate_document_state()
       reads Contract.overall_risk / policy_decisions_json /
       interaction_decisions_json (whichever the active mode populated)
       -> one of 6 states, rendered identically on /dashboard, /history,
          and /contract/{id}/review (all three wired, confirmed Phase 0)
  -> USER RESULT
```

## What this branch changed relative to the prior branch

1. **Phase 0**: two findings not previously stated as sharply — the
   shadow-mode default gating the entire modern engine, and the absence
   of any environment-variable-driven configuration for the semantic
   layer.
2. **Phase 12 (partial)**: `fact_admission.semantic_discovery_enabled()`
   makes every adapter's flag environment-configurable, plus one global
   `FACT_ADMISSION_MODE=enforced` switch. Defaults unchanged.

## What this branch did NOT change (and why)

- **`policy_enforcement.py`'s mode-branching logic itself** — not
  touched. Flipping `POLICY_ENFORCEMENT_MODE` to `"cutover"` in a real
  deployment is a production activation decision (Phase 16 of the
  mission), gated behind Phase 15's hard release gates, none of which
  this session can satisfy (no live-model frozen corpus, no live-product
  validation — see FROZEN_CORPUS_MANIFEST.md / FINAL_VALIDATION_REPORT.md).
  Making that change without satisfying the gates the mission itself
  defines would be the exact failure mode the mission opens by warning
  against ("Do not declare success because tests compile").
- **The canonical context package (Phase 1)** — not built as a distinct,
  structured object. Today, `fact_admission.discover_candidate_spans()`
  and `verify_candidate_proposition()` both receive the FULL document
  text (not a bounded excerpt), which already gives the model access to
  headings, definitions, cross-references, and party language anywhere in
  the document — but this is "send everything" rather than a deliberately
  constructed, source-coordinate-preserving context package with
  explicitly separated fields (heading / definitions / party roles /
  referenced provisions) the mission's Phase 1 describes. See
  RESIDUAL_RISK_REGISTER.md — this is flagged as a real architectural gap
  relative to the mission's ask, not silently treated as satisfied.
- **12/12 adapters' condition/proviso/exception preservation onto
  `CandidateMaterialFact`** — the schema has the fields; no adapter
  populates them from the semantic layer today (they rely entirely on
  each adapter's own pre-existing deterministic condition detection,
  which does run over semantically-discovered text, but the AI's own
  contextual read of qualifiers, per Phase 2's explicit requirement, is
  not captured as structured data). See RESIDUAL_RISK_REGISTER.md.
- **Indemnification's migration onto the shared framework** — deliberately
  left on its own pre-existing, separately-frozen mechanism (unchanged
  rationale from the prior branch: migrating a Step-4B-validated system
  for no safety benefit is not this mission's ask).

## Authority boundary (unchanged, re-verified)

See AUTHORITY_BOUNDARY.md. No new code path from an AI call to a
`policy_engine_core` decision state was introduced or found.
