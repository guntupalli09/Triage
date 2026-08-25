PHASE 6 — RE-TRACE ALL 12 ADAPTERS AFTER BLOCKERS 1-4

For each adapter: AI contextual discovery → semantic verification → deterministic grounding →
canonical fact → qualifiers → definitions → cross references → competing readings →
unresolved dependencies → reconciliation → primary fact consumption → deterministic policy
decision.

| Adapter | Real provider | Verification-error propagation | Primary fact safety | Condition | Exception | Definition | Cross-reference | Competing readings | Reconciliation | Material uncertainty blocks clean | Final |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 limitation_of_liability | PASS (env-gated) | PASS (fixed, Blocker 1+2) | PASS | PASS | PASS | PASS | PASS | PASS | PASS (single/amendment/consistent/unreconciled) | PASS | **12/12** |
| 02 indemnification | PASS (fixed, Blocker 4) | PASS (fixed, Blocker 1+3, two layers) | PASS (own 4-signal absence gate, unchanged) | PASS | PASS (fixed, Blocker 3 layer 2) | PASS | PASS | PASS | PASS (per-direction, non-merging, unchanged) | PASS | **12/12** |
| 03 confidentiality | PASS (env-gated) | PASS (unconditional consumption, no gate needed) | PASS | PASS | PASS | PASS | PASS | PASS | N/A (single-clause) | PASS | **12/12** |
| 04 payment_terms | PASS (env-gated) | PASS (fixed, Blocker 1+2) | PASS | PASS | PASS | PASS | PASS | PASS | N/A (single-clause) | PASS | **12/12** |
| 05 ip_ownership | PASS (env-gated) | PASS (fixed, Blocker 1+2 for the note-suppression path) | **KNOWN RESIDUAL GAP** — see below | PASS | PASS | PASS | PASS | PASS | N/A (single-clause) | PARTIAL | **11/12** |
| 06 insurance | PASS (env-gated) | PASS (fixed, Blocker 1+2) | PASS | PASS | PASS | PASS | PASS | PASS | N/A (single-clause) | PASS | **12/12** |
| 07 data_security | PASS (env-gated) | PASS (fixed, Blocker 1+2) | PASS | PASS | PASS | PASS | PASS | PASS | N/A (single-clause) | PASS | **12/12** |
| 08 governing_law | PASS (env-gated) | PASS (unconditional consumption, no gate needed) | PASS | PASS | PASS | PASS | PASS | PASS | N/A (single-clause) | PASS | **12/12** |
| 09 termination | PASS (env-gated) | PASS (unconditional consumption, no gate needed) | PASS | PASS | PASS | PASS | PASS | PASS | N/A (rights list, non-merging) | PASS | **12/12** |
| 10 warranties | PASS (env-gated) | PASS (already scoped inside found_anything, no gate needed) | PASS | PASS | PASS | PASS | PASS | PASS | N/A (category list) | PASS | **12/12** |
| 11 sla | PASS (env-gated) | PASS (already scoped inside found_anything, no gate needed) | PASS | PASS | PASS | PASS | PASS | PASS | N/A (single-clause) | PASS | **12/12** |
| 12 assignment | PASS (env-gated) | PASS (unconditional consumption, no gate needed) | PASS | PASS | PASS | PASS | PASS | PASS | N/A (single-clause) | PASS | **12/12** |

## ip_ownership's known residual gap (11/12) — explicitly NOT one of the 5 authorized blockers

`extract_ip_facts`'s admitted-candidate condition/exception composition loop
(`ip_ownership_policy_engine.py`, ~line 720: `for candidate in admitted_semantic:
facts.ai_identified_condition = facts.ai_identified_condition or candidate.condition; ...`)
composes a grounded AI qualifier onto the decision-facing fields whenever the candidate is
`ADMITTED` — regardless of whether the deterministic `ownership_attributions` already fully
established ownership. For genuinely colloquial ownership text
("...shall be owned exclusively by Customer upon full payment."), whether the verifier
happens to ground "upon full payment" as a `condition` varies by real-provider sampling,
producing `ACCEPT` (candidate NOT_ADMITTED that run, no qualifier composed) vs
`REQUIRES_REVIEW` (candidate ADMITTED that run, qualifier composed) across identical input.
Confirmed via `git diff` against every commit in this mission: this code path was never
touched. This is a genuine, pre-existing failure class, structurally distinct from all five
authorized blockers (it is not a verification-error propagation issue, not a note-suppression
issue, not indemnification-specific, not provider-configuration, not a UI-surface issue), and
per the mission's explicit "do not fix beyond the five authorized blockers without
justification" instruction, it was documented, not fixed. It is the reason the overall
mission verdict is `NOT READY FOR NEW INDEPENDENT FROZEN CORPUS` — see
`FINAL_REMEDIATION_VERDICT.md`.

REQUIRED FINAL PER THE MISSION'S OWN FORMAT: **11/12** (not 12/12) — reported honestly rather
than rounded up, since a genuine, confirmed instance of material-uncertainty-not-blocking-
clean exists in one adapter, discovered by this mission's own repeatability testing.
