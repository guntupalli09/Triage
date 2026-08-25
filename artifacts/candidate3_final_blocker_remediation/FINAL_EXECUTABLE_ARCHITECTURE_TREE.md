PHASE 14 — FINAL EXECUTABLE ARCHITECTURE TREE (post-remediation)

This supersedes `artifacts/pre_freeze_architecture/FINAL_EXECUTABLE_ARCHITECTURE_TREE.md` only
where this mission's fixes changed behavior; the overall pipeline shape (including the
`POLICY_ENFORCEMENT_MODE` shadow/cutover fork, which was explicitly out of scope — Blocker #6)
is unchanged and that document remains the authoritative full trace of the surrounding
pipeline. This tree shows only what actually changed.

```
CUSTOMER CONTRACT
  │
  ▼
EXTRACTION
  │
  ├── insufficient ──► ERROR / REVIEW (unchanged)
  │
  └── sufficient
        │
        ▼
NORMALIZATION
        │
        ├───────────────────────────┐
        ▼                           ▼
DETERMINISTIC DISCOVERY      AI CONTEXTUAL DISCOVERY
  (unchanged per-adapter        (Blocker 4: indemnification now follows the
  regex, per adapter)           SAME fact_admission.semantic_discovery_enabled
                                 activation path as the other 11 adapters —
                                 default unchanged, SIMULATED; FACT_ADMISSION_
                                 MODE=enforced now also activates it)
        │                           │
        │                           ▼
        │                    SEMANTIC VERIFICATION
        │                           │
        │               ┌───────────┴────────────┐
        │               ▼                        ▼
        │           VERIFIED               ERROR/UNCERTAIN
        │               │                  (Blocker 1: the COMPLETE 6-state
        │               │                  unsafe vocabulary is now audited;
        │               │                  VERIFICATION_ERROR specifically
        │               │                  now escalates UNCONDITIONALLY,
        │               │                  where it previously vanished)
        │               ▼                        │
        │       DETERMINISTIC GROUNDING           ▼
        │               │                  UNRESOLVED FACT
        │               │                  (Blocker 2: only escalated when
        │               │                  no GENUINE, POSITIVE deterministic
        │               │                  finding for the SAME provision/
        │               │                  obligation already exists —
        │               │                  specific mechanisms [definition/
        │               │                  cross-reference/competing-reading]
        │               │                  are now UNCONDITIONAL and never
        │               │                  suppressed by this gate at all)
        └───────────────┼────────────────────────┘
                        ▼
                  RECONCILIATION
        (Blocker 3: indemnification's reconciliation channel now has an
        equivalent-strength materiality gate to liability's, closed in two
        layers -- monetary/scope/condition-established AND no uncaptured
        same-clause exception signal)
                        │
           ┌────────────┴─────────────┐
           ▼                          ▼
      SAFE FACT                  UNCERTAINTY
           │                          │
           ▼                          ▼
    POLICY ADAPTER             BLOCK CLEAN
           │                   REQUIRES_REVIEW
           ▼
12 DETERMINISTIC POLICY DECISIONS
  (11/12 fully closed against material-uncertainty-blocks-clean; ip_ownership
  carries one KNOWN, documented, out-of-scope residual gap in its admitted-
  candidate qualifier-composition loop -- unrelated to Blockers 1-5, not
  fixed this mission -- see TWELVE_ADAPTER_PROOF_MATRIX.md)
           │
           ▼
CROSS-POLICY INTERACTION ENGINE (unchanged, already sound per the pre-freeze
  inspection)
           │
           ▼
AUTHORITATIVE DOCUMENT AGGREGATION (unchanged logic; Blocker 5 wired FOUR
  additional customer surfaces to consume it)
           │
    ┌──────┼──────┬────────┬────────┬─────────┬──────────┐
    ▼      ▼      ▼        ▼        ▼         ▼          ▼
 REVIEW  DASH  HISTORY  FULL REPORT PDF  NEGOTIATION  EXTERNAL
 (was OK)(OK)   (OK)     (FIXED)  (FIXED)  PACKAGE     SHARE
                                            (FIXED)    (FIXED)
```

Executable reality confirmed: all four newly-wired surfaces reuse the pre-existing
`_document_state_for_contract` helper — no parallel, second aggregation implementation was
created, and the anonymous token-based flow (which never runs policy enforcement at all) was
correctly left unmodified rather than force-fitted into this tree.
