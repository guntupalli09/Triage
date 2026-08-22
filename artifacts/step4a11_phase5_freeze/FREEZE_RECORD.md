# Step 4A.11 Phase 5 — Candidate Freeze Record

## Frozen identity

- **Git SHA (frozen):** d769491b23e3aa570f80f492f91a30c758806367
- **Branch:** claude/triage-counsel-audit-44xogk
- **Freeze timestamp:** 2026-08-22 (session date)
- **Python runtime:** Python 3.11.15
- **Semantic provider:** SIMULATED (semantic_discovery.py) — no real LLM/embedding
  provider is reachable from this sandboxed session; this module stands in for one
  and is implemented as ordinary Python solely to exercise the authority-boundary
  architecture end to end. Its recall numbers are NOT representative of a real
  model's recall. See semantic_discovery.py's own module docstring.
- **Discovery mode:** HYBRID_DISCOVERY_ENABLED = True (indemnification_policy_engine.py:79)
  — regex/structural discovery always runs; semantic discovery runs additively and
  can only PROPOSE candidate spans for deterministic verification, never establish
  a fact directly. Liability and payment_terms engines have NO semantic discovery
  layer at all — 100% structural/regex by construction.

## Production files participating in policy decisions (SHA-256)

| File | SHA-256 |
|---|---|
| policy_engine_core.py | a66531ed3f2025ce2baff1b12393afd5264fba56ac509e2b347740466e80dda3 |
| indemnification_policy_engine.py | 3863653e49c282c1da20125b794e386576a5e0f682c179ff9dd2a0fa0501f134 |
| liability_policy_engine.py | e01f932c4efbf87f9a7e3ce9091c80c17cd78937000d6c48fc83ec02e07b7659 |
| payment_terms_policy_engine.py | 28f50ef1c4de5cb9fe63b230722580f111d762c5f39ff09ce7699f0fb451f5d8 |
| semantic_discovery.py | c0b4e7c7229d3ac6491f2310224abe98182e9a79fb4d3f720ac29d96dbadd8f6 |

## Pre-freeze control run (final, this record)

- pytest (broad, excluding 44 files that fail to COLLECT in this sandbox due to
  missing unrelated third-party deps — httpx2/dotenv — pre-existing before this
  session, confirmed identical via git-stash A/B comparison): **1210 passed / 10
  failed (pre-existing, unrelated to policy engines) / 14 skipped**
- Liability historical benchmark: **95.2% policy-state accuracy — PASS**
- Indemnification historical benchmark: 1 known pre-existing gap (xref-04) — unchanged
- Payment terms historical benchmark: **100% — PASS, false-safe=0, false-escalation=0, determinism=100%**
- Step 4A.10.1 S4 benchmark: **false operative extraction on non-operative text = 0**
- Step 4A.10.1 symmetry benchmark: **False Symmetry (FS) = 0**
- Phase 1 cross-reference DEV benchmark: **false_established=0, wrong_value_while_established=0**
- Phase 2 conditional-applicability DEV benchmark: **100% exact status match, stripped-condition=0**
- Phase 3 structural risk-transfer DEV benchmark: **false_established=0, wrong_roles_while_established=0**
- Phase 4 fresh adversarial battery (174 cases): **CA=109 CR=39 FE=23 WC=3 SM=1**,
  semantic_authority_diffs=0, determinism mismatches=0 (5x repeat)
- Role resolution benchmark: conflict precision 100%, recall 94.4% (1 known FN, unchanged)
- Role boundary benchmark: exact-boundary recall 100% (33/33), 1 known ALL-CAPS FP (unchanged)
- Step 4A.7.2 role attribution benchmark: **false_safe=0, unnecessary_review=0**
- test_step4a9_1_hybrid_authority_boundary + test_step4a9_2_real_provider_adversarial: **19 passed, 1 skipped**
- step4a10_outage_and_malicious.py (timeout/outage/malformed/empty/rate-limit/
  invalid-schema/wrong-actor/wrong-cap/wrong-policy-result/accept-injection/
  fabricated-explanation): **every injection/fabrication attack REJECTED; provider
  outage never silently becomes CONFIRMED_ABSENT when regex independently hits**

## Hard gate confirmation (final, pre-freeze)

| Gate | Value | Status |
|---|---|---|
| S4 (false operative extraction) | 0 | PASS |
| False symmetry | 0 | PASS |
| Semantic→authority | 0 | PASS |
| Fabricated-evidence→authority | 0 | PASS |
| Policy-changing UNVERIFIED-CA | 0 | PASS |
| False-candidate→wrong-clean | 0 | PASS |
| Authoritative determinism | 100% | PASS |

No hard invariant failed. Per Phase 5 protocol: **THE CURRENT PRODUCTION COMMIT IS
DECLARED FROZEN** at d769491b23e3aa570f80f492f91a30c758806367.

## Known, carried-forward development findings (NOT re-tuned; carried as attack targets)

1. **3 WC — ALL-CAPS heading/provision-boundary cases** (fab-ind-af6-heading-01,
   fab-pay-af6-heading-01, fab-pay-af6-heading-only-02). A heading-ratio detection
   fix was attempted and reverted this session after it regressed 2 real historical
   liability benchmark cases (malformed-05, unheaded-08). Left as a disclosed,
   accepted limitation.
2. **1 SM — liability lacks a broad, non-authoritative discovery signal** analogous
   to indemnification's `_risk_transfer_signal_present`. A verbose, unusually-worded
   but genuinely present cap concept can return a hard CONFIRMED_ABSENT (`None`)
   rather than routing to review. Disclosed, not fixed (architecture-level change,
   out of scope for this freeze).

NO PRODUCTION MODIFICATION IS PERMITTED FROM THIS POINT FORWARD DURING STEP 4A.11
FINAL VALIDATION.
